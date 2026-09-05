# Corpus provenance

`pg_tde/` vendors the documentation tree from
[percona/pg_tde](https://github.com/percona/pg_tde), sparse-checked out at
`documentation/` only.

| | |
|---|---|
| Upstream commit | `cef89082e01b06fe2ac1cd7d2f845124d46f5828` |
| Commit date | 2026-09-03T11:14:50Z |
| Vendored on | 2026-09-05 |
| Path | `documentation/docs` |

The tests in `tests/test_findings.py` assert against this snapshot. If upstream
fixes a defect, the matching test starts failing, which is the signal to
refresh the corpus and delete the test.

This directory is Percona's work and carries Percona's license, not this
project's.
