#!/usr/bin/env bash
# The same row is written to an ordinary table and a tde_heap table.
# Ask PostgreSQL where each one lives, then read the raw files.
set -euo pipefail

NAME="${ASSAY_DEMO_CONTAINER:-assay-demo}"

docker exec -i "$NAME" bash -s <<'EOF'
set -e
q() { sudo -u postgres psql -tAc "$1"; }

DATA=$(q "SHOW data_directory;")
PLAIN=$(q "SELECT pg_relation_filepath('plain_albums');")
ENC=$(q "SELECT pg_relation_filepath('albums');")

echo "pg_tde_is_encrypted('plain_albums') = $(q "SELECT pg_tde_is_encrypted('plain_albums');")"
echo "pg_tde_is_encrypted('albums')       = $(q "SELECT pg_tde_is_encrypted('albums');")"
echo
echo "grep the canary string in the raw heap files:"
printf '  plain_albums  %s occurrences\n' "$(sudo grep -c KIND_OF_BLUE_CANARY "$DATA/$PLAIN" || true)"
printf '  albums (tde)  %s occurrences\n' "$(sudo grep -c KIND_OF_BLUE_CANARY "$DATA/$ENC" || true)"
echo
echo "the readable one, in context:"
sudo grep -ao '.\{0,12\}KIND_OF_BLUE_CANARY.\{0,4\}' "$DATA/$PLAIN" | head -1 | sed 's/^/  /'
EOF
