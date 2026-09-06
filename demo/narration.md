# Narrated walkthrough: shot list and script

For the screen recording. Target 3 minutes 30, which is long enough to show
the finding and short enough for LinkedIn. Shorter is better than complete.

Record at 1440p or higher, terminal font at 16pt or larger. Phone viewers are
most of the audience and small type kills it.

**Before you hit record:** run `./demo/provision.sh` and let it finish. It
takes about two minutes and there is nothing to see. Then open two terminal
tabs, one in the repo, one for the container.

A note on delivery, since it is the thing that will actually carry this: the
finding is genuinely interesting, so let it be interesting on its own. No
build-up, no "and here's the crazy part." State what happened and pause. The
pauses are where the viewer catches up.

---

## Shot 1 — Cold open, no preamble (0:00–0:25)

**On screen:** the published Percona install page in a browser, scrolled to
the "Install pg_tde" section, with `percona-pg-tde(pg-version)` visible.

> There is a job open at Percona for a technical writer on PostgreSQL. Rather
> than tell them I know their product, I went and executed their documentation
> against a real server.
>
> This is their install page. That line is the one I want to start with.

Do not say "hi everyone" or introduce yourself. The first sentence should be
the premise.

---

## Shot 2 — The syntax error (0:25–0:55)

**On screen:** terminal. Paste the line exactly as published.

```
$ sudo apt-get install -y percona-pg-tde(pg-version)
bash: syntax error near unexpected token `('
```

> Parentheses are shell metacharacters, so this is not a wrong package name.
> It is a syntax error.
>
> The correct example is directly underneath it and works fine, so a careful
> reader recovers. But that block is styled exactly like the five correct
> blocks above it. It has earned your trust and then spent it.
>
> It is also on the yum page, and twice on the uninstall page. So it is a
> template, not a typo.

---

## Shot 3 — The real finding (0:55–1:50)

This is the shot that matters. Slow down here.

**On screen:** the container, immediately after completing the documented
install path.

```
$ dpkg -l | grep -E 'percona|postgres'
libpq5:arm64        3:18.6-1.noble
percona-pg-tde18    1:2.2.2-1.noble
percona-release     1.0-34.generic

$ command -v postgres psql pg_ctlcluster initdb
```

> I finished the install page. Then I clicked its Next Steps button, which goes
> to the configuration page, and that page opens by telling you to connect with
> psql as a superuser.

*(pause, then run the `command -v` line and let the empty output sit)*

> There is no psql. There is no server, no cluster, no postgres user. What the
> documented install gives you is the extension and the client library, waiting
> for a database that was never mentioned.
>
> The missing package is `percona-ppg-server-18`. It does not appear anywhere in
> the install path.
>
> If you already run Percona's distribution, this never touches you. If you
> arrived because you searched for how to encrypt a PostgreSQL database, you
> complete two pages, hit a wall, and have no idea which of the last twenty
> commands went wrong.

Let the empty output sit on screen for a full two seconds before speaking. It
is the whole point of the video.

---

## Shot 4 — Why a tool (1:50–2:30)

**On screen:** `assay lint corpus/pg_tde/documentation/docs --expect-major 18`

> Finding that by hand took an afternoon. Finding it again next month would take
> another afternoon, which means nobody does it. So it had to become something
> that runs.
>
> This is the static half. It reads Markdown, needs no container, and is fast
> enough for every pull request.

*(let the output scroll, then scroll back to a FAIL line)*

> Eight failures across the doc set. A shell command tagged as SQL. Pages that
> inspect tables they never created. A hardcoded version 17 in a doc set that
> ships 18.

---

## Shot 5 — The mistake (2:30–3:00)

Do not skip this. It is the part that makes the rest credible.

**On screen:** the run report, on the `BLOCKED` line.

> The first time I ran the execution half, it told me there were sixteen
> failures.
>
> There are not sixteen bugs. There is one missing server, and then thirteen
> commands that fail because of it. A tool that reports that as sixteen defects
> is not being thorough, it is inflating its own findings, and the first
> maintainer who reads it correctly decides the tool is noise.
>
> So it attributes cascades now. Three defects, thirteen blocked, and the
> thirteen are listed as evidence rather than counted as findings.

---

## Shot 6 — It works (3:00–3:25)

**On screen:** `./demo/prove-encryption.sh`

> None of this is a complaint about the feature. Supply the missing install and
> the whole path works exactly as documented.
>
> Same row, written to an ordinary table and an encrypted one. Readable in the
> raw heap file of one, absent from the other.

*(pause on the two grep counts)*

> There is something very satisfying about a security feature you can confirm
> with grep.

---

## Shot 7 — Close (3:25–3:40)

**On screen:** the README, or just the terminal.

> The findings are going upstream. But the thing under the findings is that none
> of these were hard to catch. Every one came from a few hundred lines of Python
> doing the least imaginative thing available, which is running the commands.
>
> We moved documentation into git, put it through pull requests and CI, and
> called it docs-as-code. And then declined to do the one thing that makes code
> code, which is executing it to see whether it works.

Stop there. No sign-off, no subscribe.

---

## If you want the ninety-second cut

Shots 1, 3 and 6 only. The syntax error and the calibration story are the two
that get dropped, in that order.
