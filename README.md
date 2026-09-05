# assay

Execute the documentation. Find out what is still true.

Documentation rots quietly. A code sample keeps its syntax highlighting long
after the function it calls was renamed, and nothing in a normal docs pipeline
notices, because a docs build checks that a page renders, not that it works.
The reader finds out instead.

`assay` runs the page. It pulls the commands out of Markdown, executes them
against a real server in a container, and reports where a reader following
along would stop.

```
$ assay run manifests/pg_tde.yaml

assay run  assay-host:ubuntu24

  PASS  4   FAIL  3   BLOCKED  13   ADAPTED  4   SKIPPED  0

  Adapted commands are harness limitations, not doc defects:
    setup.md:32  no init system in a container; pg_ctlcluster is Debian's documented equivalent

  FAIL  apt.md:56
       $ sudo apt-get install -y percona-pg-tde(pg-version)
       exit 2
      bash: syntax error near unexpected token `('

  FAIL  setup.md:22
       $ ALTER SYSTEM SET shared_preload_libraries = 'pg_tde';
       exit 1
      sudo: unknown user postgres

  13 further commands could not run; all blocked by setup.md:22
  They are downstream of one root cause, not separate defects.

  3 documentation defects -> exit 1
```

## The two halves

**`assay lint`** is static. It reads Markdown, finds nothing, and needs no
container, so it is cheap enough to run on every pull request.

```
$ assay lint docs/ --expect-major 18
```

| Rule | Fires on |
|---|---|
| L001 | A placeholder left inside a block the reader is told to run |
| L002 | A fence tagged `sql` whose content is a shell command, or the reverse |
| L003 | A page that inspects a table it never created |
| L004 | A hardcoded major version the doc set has moved past |

**`assay run`** is the thorough half. It boots one container, walks a
documentation path in reading order, and executes each block into the same
machine.

```
$ assay run manifests/pg_tde.yaml
```

## Why one container, in order

Documentation is a chain. Page three assumes what page one told you to install,
and the defect worth finding is a page assuming state that no earlier page
establishes. Run each page in a fresh container and that defect is invisible,
because every page looks fine in isolation.

So a run is one machine, and pages execute in the order the docs link them.
That is what surfaced the largest finding in `findings/pg_tde-2.2.2.md`: the
pg_tde install page completes successfully, its Next steps button sends you to
a page that needs a running server, and nothing in between ever installs one.

## The three outcomes, and why the third one exists

```
pass       the command ran and returned success
fail       the command ran and failed where it should have worked -> a defect
adapted    the command could not run for a reason that is the harness's fault,
           and a declared substitute ran instead -> never counted as a defect
```

`adapted` is the load-bearing one. There is no init system in a container, so
`systemctl restart postgresql` cannot work, and counting that as a documentation
bug would be wrong. Every substitution is declared in the manifest, printed in
the report, and carries a written reason, so a reader can disagree with it:

```yaml
substitutions:
  - match: "systemctl restart postgresql"
    replace: "sudo pg_ctlcluster 18 main restart"
    reason: "no init system in a container; pg_ctlcluster is Debian's documented equivalent"
```

A tool that reports environment noise as findings gets muted within a week.

## Calibration

Rules are tuned against a real corpus before they ship, and the tuning is in
the tests.

Uncalibrated, L003 reported eleven failures on the pg_tde docs. Four were real.
The rest were system catalogs nobody creates (`pg_stat_replication`) and
fragment pages that use a generic table name on purpose (`mytable`). Those are
now a `note`, not a failure, and `tests/test_findings.py` pins both the
defects the rule must catch and the shapes it must not.

The same discipline applies to the run: sixteen commands failed on the pg_tde
path, and the report says three defects, because thirteen of them were one
missing server cascading downstream.

## Install

```
pip install -e .
```

Python 3.9 or newer. `assay run` needs Docker.

## The corpus

`corpus/` vendors the [percona/pg_tde](https://github.com/percona/pg_tde)
documentation at a pinned commit, so the tests have something real and stable
to assert against. It is Percona's work, under its own license.

`findings/pg_tde-2.2.2.md` is the write-up of what the tool found there, with
the environment, the commands, and the observed output for each item.

## License

Apache-2.0.
