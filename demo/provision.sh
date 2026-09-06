#!/usr/bin/env bash
# Bring up a working Percona Server for PostgreSQL 18 with pg_tde encryption,
# following the published documentation and supplying the one step it omits.
#
# This is the corrected path. `assay run manifests/pg_tde.yaml` walks the
# documented path and shows where it breaks; this script is what the docs
# should have said, so there is something to demonstrate at the end of it.
#
#   ./demo/provision.sh          build it
#   ./demo/prove-encryption.sh   show that the encryption is real
#
set -euo pipefail

NAME="${ASSAY_DEMO_CONTAINER:-assay-demo}"
IMAGE="assay-host:ubuntu24"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "building $IMAGE"
  docker build -q -t "$IMAGE" -f "$here/../docker/Dockerfile.host" "$here/.." >/dev/null
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --platform linux/arm64 "$IMAGE" >/dev/null

run() { docker exec -i "$NAME" bash -s; }

echo "==> repository setup, per apt.md steps 1-5"
run <<'EOF'
set -e
sudo apt-get update -qq
sudo apt-get install -y -qq wget gnupg2 curl lsb-release >/dev/null
sudo wget -q https://repo.percona.com/apt/percona-release_latest.generic_all.deb
sudo dpkg -i percona-release_latest.generic_all.deb >/dev/null 2>&1
sudo percona-release enable-only ppg-18 >/dev/null 2>&1
sudo apt-get update -qq
EOF

echo "==> the step apt.md never mentions: install a database server"
run <<'EOF'
set -e
sudo apt-get install -y -qq percona-ppg-server-18 >/dev/null
EOF

echo "==> pg_tde, per apt.md step 7"
run <<'EOF'
set -e
sudo apt-get install -y -qq percona-pg-tde18 >/dev/null
sudo pg_ctlcluster 18 main start
EOF

echo "==> setup.md: preload the extension and restart"
run <<'EOF'
set -e
sudo -u postgres psql -q -c "ALTER SYSTEM SET shared_preload_libraries = 'pg_tde';"
sudo pg_ctlcluster 18 main restart
sudo -u postgres psql -q -c "CREATE EXTENSION pg_tde;"
EOF

echo "==> keyring.md: key provider, principal key"
run <<'EOF'
set -e
sudo -u postgres psql -q <<'SQL'
SELECT pg_tde_add_database_key_provider_file('file-keyring', '/tmp/pg_tde_test_local_keyring.per');
SELECT pg_tde_create_key_using_database_key_provider('my_default_key', 'file-keyring');
SELECT pg_tde_set_key_using_database_key_provider('my_default_key', 'file-keyring');
SQL
EOF

echo "==> two tables, one encrypted, same row in both"
run <<'EOF'
set -e
sudo -u postgres psql -q <<'SQL'
CREATE TABLE plain_albums (title TEXT NOT NULL) USING heap;
CREATE TABLE albums (title TEXT NOT NULL) USING tde_heap;
INSERT INTO plain_albums (title) VALUES ('KIND_OF_BLUE_CANARY');
INSERT INTO albums       (title) VALUES ('KIND_OF_BLUE_CANARY');
CHECKPOINT;
SQL
EOF

echo
echo "ready. container: $NAME"
docker exec "$NAME" bash -lc 'sudo -u postgres psql -tAc "select version();"'
