# Findings: pg_tde documentation, as of percona-pg-tde18 1:2.2.2-1.noble

Every item below was found by executing the published page against a live
server, not by reading it. Each one names the command, the observed output, and
what a reader is left holding.

## Environment

| | |
|---|---|
| Host | Ubuntu 24.04.4 LTS, aarch64, in a container with a non-root user and working `sudo` |
| Server | Percona Server for PostgreSQL 18.6.1 (`percona-ppg-server-18` 1:18.6-4.noble) |
| Extension | `percona-pg-tde18` 1:2.2.2-1.noble |
| Repository | `repo.percona.com/ppg-18/apt` noble, arm64 |
| Date | 5 September 2026 |
| Reproduce | `assay run manifests/pg_tde.yaml` |

Two commands could not be run as written, for reasons that are the harness's
fault and not the documentation's. Both are declared in the manifest and
reported as `adapted` rather than counted as defects:

- `systemctl restart postgresql` has no init system to talk to in a container.
  Substituted with `pg_ctlcluster 18 main restart`, Debian's documented
  equivalent.
- Apt lists were primed before starting, because a freshly provisioned Ubuntu
  server has them and a container image ships with them deleted. Without this,
  the docs would appear to be missing an `apt-get update` that they are right
  to omit.

---

## 1. Completing the install page leaves you with no PostgreSQL server

**Severity: high.** This breaks the documented path from end to end for anyone
who has not already installed Percona Server for PostgreSQL.

`apt.md` ends by installing `percona-pg-tde18`, and its Next steps button goes
directly to `setup.md`. Following both pages in order, what you have after the
install page is:

```
$ dpkg -l | grep -E 'percona|postgres'
libpq5:arm64        3:18.6-1.noble
percona-pg-tde18    1:2.2.2-1.noble
percona-release     1.0-34.generic

$ command -v postgres psql pg_ctlcluster initdb
(nothing)
```

The package delivers `pg_tde.so` and the `pg_tde_*` command line tools into
`/usr/lib/postgresql/18/`, and nothing else. There is no server, no `psql`, no
cluster, and no `postgresql` systemd unit.

`setup.md` then opens by telling you to edit `postgresql.conf`, or to run
`ALTER SYSTEM` in `psql` as a superuser, and to restart the `postgresql`
service. Executed in order, the first command that touches the server fails:

```
$ sudo -u postgres psql -c "ALTER SYSTEM SET shared_preload_libraries = 'pg_tde';"
sudo: unknown user postgres
```

Thirteen further commands across `setup.md`, `keyring.md` and `test.md` cannot
run, all for this one reason.

The missing step is `sudo apt-get install -y percona-ppg-server-18`, which is
never named anywhere in the install path. The page's Preconditions section
assumes Percona Server for PostgreSQL is present, but does not say so and does
not link to its install guide.

**Suggested fix:** add the server install to `apt.md` and `yum.md`, or state
the prerequisite explicitly in Preconditions with a link.

---

## 2. `percona-pg-tde(pg-version)` is a shell syntax error, on three pages

**Severity: medium.** Confirmed on the published site, not only in the source.

The install pages present this in a copy-pasteable block:

```
sudo apt-get install -y percona-pg-tde(pg-version)
```

Parentheses are shell metacharacters, so this is not merely a wrong package
name:

```
bash: syntax error near unexpected token `('
```

The intent is clear from the worked example directly below it
(`percona-pg-tde18`), so a careful reader recovers. A reader who copies the
first block, as the page's own structure invites, does not.

It appears on `apt.md:56`, `yum.md:28`, and twice in `how-to/uninstall.md`
(lines 55 and 111), which makes it a template defect rather than one page's
typo.

**Suggested fix:** render the placeholder outside the code block, or use a
shell-safe form such as `percona-pg-tde<pg-version>` shown as inline code.

---

## 3. A shell command is tagged as SQL

**Severity: medium.**

`setup.md:59`, the optional step for enabling the extension by default:

````
```sql
psql -d template1 -c 'CREATE EXTENSION pg_tde;'
```
````

The three blocks above it on the same page are correctly tagged `sql` and are
genuinely SQL, so the tag has earned the reader's trust by the time they reach
this one. Pasted into `psql`, as the tag instructs:

```
ERROR:  syntax error at or near "psql"
LINE 1: psql -d template1 -c 'CREATE EXTENSION pg_tde;'
        ^
```

Run in a shell, it works.

**Suggested fix:** retag as `bash`.

---

## 4. A postgresql.conf directive is tagged as bash

**Severity: low.**

`setup.md:16` offers the `shared_preload_libraries` setting as a shell block:

```
shared_preload_libraries = 'pg_tde'
```

Executed:

```
bash: shared_preload_libraries: command not found
```

The surrounding prose does say to add the line to `postgresql.conf`, so this is
recoverable from context. Tagging it `ini` would remove the ambiguity.

---

## 5. The validation page's stated precondition is wrong

**Severity: medium.**

`test.md` opens: "After enabling the `pg_tde` extension for a database, you can
begin encrypting data using the `tde_heap` table access method."

That is not sufficient. With the extension created and no principal key
configured, the page's own worked example fails:

```
$ CREATE TABLE albums (...) USING tde_heap;
ERROR:  principal key not configured
HINT:  Use pg_tde_set_key_using_database_key_provider() or
       pg_tde_set_key_using_global_key_provider() to configure one.
```

The server's hint is good, and key configuration is documented on other pages,
so the information exists. The defect is that this page states a precondition
it does not actually meet and then presents an example that cannot run.

**Suggested fix:** state that a configured principal key is required and link
to the key provider pages, which `setup.md` already does in its Next steps.

---

## 6. Two pages inspect objects they never created

**Severity: low, but they are the first thing a reader tries.**

`test.md:28` creates `albums`, then checks a different table:

```
$ SELECT pg_tde_is_encrypted('table_name');
ERROR:  relation "table_name" does not exist
```

`global-key-provider-configuration/keyring.md:57` creates `customer_table`,
then its tip says:

```
$ \d+ test1
Did not find any relation named "test1".
```

**Suggested fix:** use the names each page actually creates.

---

## 7. The keyring page recommends the wrong key info function

**Severity: medium.** This is the subtlest one and the easiest to miss.

`keyring.md` walks a **database-scoped** key provider, then offers this tip:
"You can check the default key information (such as the date and time of
creation). Run: `SELECT pg_tde_default_key_info();`"

Having followed that page exactly, the function returns four empty fields:

```
-[ RECORD 1 ]-----+-
key_name          |
provider_name     |
provider_id       |
key_creation_time |
```

`pg_tde_default_key_info()` reports the *default* key, set via a global
provider. The page set a database key, whose info lives elsewhere:

```
$ SELECT * FROM pg_tde_key_info();
-[ RECORD 1 ]-----+------------------------------
key_name          | my_default_key
provider_name     | file-keyring
provider_id       | 1
key_creation_time | 2026-09-05 04:07:59.493923+00
```

A reader following the page sees empty output and has no way to tell whether
their key failed to set or they ran the wrong function. It is the second one.

**Suggested fix:** use `pg_tde_key_info()` in the database-scoped walkthrough.

---

## 8. Hardcoded previous major version

**Severity: low.**

`setup.md:38` tells RHEL users to run `sudo systemctl restart postgresql-17` in
a doc set that ships and documents 18. `how-to/multi-tenant-setup.md` carries
the same at lines 28 and 34. In source, the version macro is named
`{{pgversion17}}` while rendering `18`, which is how this drifts.

---

## What still works

The path is sound once the missing server install is supplied. Following
`keyring.md` verbatim after that, encryption engages and is verifiable on disk:

```
$ SELECT pg_tde_is_encrypted('albums');
 t

$ grep -c KIND_OF_BLUE_CANARY base/5/16498    # plain heap
1
$ grep -c KIND_OF_BLUE_CANARY base/5/16488    # tde_heap
0
```

The same row, written to both tables, is readable in the raw file of one and
absent from the other. The feature does what it says. The documentation is what
needs the work.
