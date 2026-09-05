"""Execution checks: walk a documentation path in one long-lived container.

The design decision that matters here is state. Documentation is a chain, not
a set of independent pages: page three assumes what page one told you to
install. Running each page in a fresh container hides exactly the defect worth
finding, which is a page assuming state that no earlier page establishes.

So one container is created for a whole run, every page executes into it in
reading order, and the run reports the first point at which the chain breaks.

Three outcomes are distinguished, and the distinction is the whole point of
trusting the report:

  pass       the command ran and returned success
  fail       the command ran and returned failure, in an environment where it
             should have worked. This is a documentation defect.
  adapted    the command could not run as written for a reason that is the
             harness's fault rather than the documentation's, and a declared
             substitute ran instead. systemctl is the standing example: there
             is no init system in a container, so `systemctl restart
             postgresql` is replaced by `pg_ctlcluster 18 main restart`.

An `adapted` result is never counted as a documentation defect. Every
substitution is declared in the manifest, printed in the report, and has to be
justified there, so a reader can decide whether they believe it.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .blocks import Block, extract, runnable, strip_prompts


# Once a prerequisite is missing, every later command fails for the same
# reason. Those are not separate defects and must not be counted as such.
CASCADE_SIGNATURES = [
    "unknown user postgres",
    "command not found: psql",
    "psql: command not found",
    "could not connect to server",
    "connection to server",
    "No such file or directory",
]


@dataclass
class Step:
    block: Block
    status: str  # pass | fail | blocked | adapted | skipped
    command: str
    exit_code: int = 0
    output: str = ""
    note: str = ""
    blocked_by: Optional[str] = None

    @property
    def is_defect(self) -> bool:
        return self.status == "fail"


@dataclass
class RunResult:
    image: str
    steps: List[Step] = field(default_factory=list)
    started: float = field(default_factory=time.time)

    def counts(self) -> Dict[str, int]:
        out = {"pass": 0, "fail": 0, "blocked": 0, "adapted": 0, "skipped": 0}
        for s in self.steps:
            out[s.status] = out.get(s.status, 0) + 1
        return out

    @property
    def defects(self) -> List[Step]:
        return [s for s in self.steps if s.is_defect]

    def attribute_cascades(self) -> None:
        """Reclassify downstream failures as blocked by the first root cause.

        Running the pg_tde install path produces sixteen failing commands. It
        does not contain sixteen bugs. One page never installs a server, and
        every later command fails with `sudo: unknown user postgres`. Reporting
        that as sixteen defects would be a tool inflating its own findings,
        which is worse than not running it.
        """
        root: Optional[Step] = None
        for step in self.steps:
            if step.status != "fail":
                continue
            if root is not None and any(sig in step.output for sig in CASCADE_SIGNATURES):
                step.status = "blocked"
                step.blocked_by = root.block.location()
                continue
            if any(sig in step.output for sig in CASCADE_SIGNATURES):
                root = step


class Container:
    """A disposable Linux host that persists for the length of one run."""

    def __init__(self, image: str, name: str = "assay-run", platform: Optional[str] = None):
        self.image = image
        self.name = name
        self.platform = platform

    def __enter__(self) -> "Container":
        subprocess.run(["docker", "rm", "-f", self.name],
                       capture_output=True, check=False)
        cmd = ["docker", "run", "-d", "--name", self.name]
        if self.platform:
            cmd += ["--platform", self.platform]
        cmd += [self.image, "sleep", "infinity"]
        subprocess.run(cmd, capture_output=True, check=True)
        return self

    def __exit__(self, *exc) -> None:
        subprocess.run(["docker", "rm", "-f", self.name],
                       capture_output=True, check=False)

    def sh(self, script: str, timeout: int = 900):
        """Run a shell script inside the container by file, never by -c.

        Passing documentation through `bash -c` on the host means the host
        shell parses it first, which quietly fixes or mangles the very quoting
        defects this tool exists to find.
        """
        p = subprocess.run(
            ["docker", "exec", "-i", self.name, "bash", "-s"],
            input=script, text=True, capture_output=True, timeout=timeout,
        )
        return p.returncode, (p.stdout + p.stderr).strip()

    def psql(self, sql: str, database: str = "postgres", timeout: int = 300):
        script = (
            "sudo -u postgres psql -v ON_ERROR_STOP=1 -d {} <<'ASSAY_EOSQL'\n"
            "{}\nASSAY_EOSQL\n"
        ).format(shlex.quote(database), sql)
        return self.sh(script, timeout=timeout)


def _adapt(command: str, substitutions: List[Dict[str, str]]):
    for sub in substitutions:
        if sub["match"] in command:
            return sub["replace"], sub.get("reason", "")
    return None, ""


def run_page(container: Container, path: str, text: str,
             substitutions: Optional[List[Dict[str, str]]] = None,
             skip_lines: Optional[List[str]] = None) -> List[Step]:
    """Execute every runnable block on one page, in reading order."""
    substitutions = substitutions or []
    skip_lines = skip_lines or []
    steps: List[Step] = []

    for block in runnable(extract(text, path)):
        body = strip_prompts(block.body).strip()
        if not body:
            continue
        if any(s in body for s in skip_lines):
            steps.append(Step(block, "skipped", body, note="skipped by manifest"))
            continue

        if block.kind == "sql":
            code, out = container.psql(body)
            steps.append(Step(block, "pass" if code == 0 else "fail",
                              body, code, out))
            continue

        replacement, reason = _adapt(body, substitutions)
        if replacement is not None:
            code, out = container.sh(replacement)
            steps.append(Step(block, "adapted", body, code, out, note=reason))
            continue

        code, out = container.sh(body)
        steps.append(Step(block, "pass" if code == 0 else "fail", body, code, out))

    return steps
