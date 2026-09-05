"""Static checks: the defects you can find without booting anything.

These run in milliseconds on a docs repo, so they belong in a docs CI pipeline
on every pull request. The execution checks in run.py are the slow, thorough
half; these are the half you can afford to run on every commit.

Every rule here fires on a defect that was first found by executing the page.
None of them are hypothetical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .blocks import Block, extract, runnable, strip_prompts

# Commands that mean "this is a shell block", whatever the fence claims.
SHELL_HEADS = {
    "sudo", "apt", "apt-get", "yum", "dnf", "dpkg", "wget", "curl", "systemctl",
    "service", "psql", "pg_ctl", "pg_ctlcluster", "pg_lsclusters", "initdb",
    "cd", "mkdir", "chmod", "chown", "export", "echo", "cat", "ls", "docker",
}

# Placeholder shapes that reach the reader's clipboard unrendered.
PLACEHOLDER_PATTERNS = [
    (r"\(\s*[a-z][a-z0-9-]*-version\s*\)", "unrendered (name-version) placeholder"),
    (r"<[a-z_][a-z0-9_]*>", "angle-bracket <placeholder>"),
    (r"\{\{\s*[a-z0-9_]+\s*\}\}", "unrendered {{macro}}"),
]

SEVERITY_ORDER = {"fail": 0, "warn": 1, "note": 2}


@dataclass
class Finding:
    rule: str
    severity: str  # fail | warn | note
    location: str
    summary: str
    detail: str = ""

    def sort_key(self):
        return (SEVERITY_ORDER.get(self.severity, 9), self.location)


def _first_word(line: str) -> str:
    line = line.strip()
    return line.split()[0] if line else ""


def _sql_identifiers_created(body: str) -> Set[str]:
    out = set()
    for m in re.finditer(r"\bCREATE\s+(?:TABLE|INDEX|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)",
                         body, re.I):
        out.add(m.group(1).lower())
    return out


def _sql_identifiers_referenced(body: str) -> Set[str]:
    out = set()
    for m in re.finditer(r"\\d\+?\s+([a-z_][a-z0-9_]*)", body):  # \d+ table
        out.add(m.group(1).lower())
    for m in re.finditer(r"pg_tde_is_encrypted\(\s*'([a-z_][a-z0-9_]*)'\s*\)", body, re.I):
        out.add(m.group(1).lower())
    for m in re.finditer(r"\bFROM\s+([a-z_][a-z0-9_]*)", body, re.I):
        out.add(m.group(1).lower())
    return out


def check_placeholder_in_runnable(blocks: List[Block]) -> List[Finding]:
    """L001 - a placeholder left inside a block the reader is told to run.

    The pg_tde install page shipped `percona-pg-tde(pg-version)`. Pasted into
    bash that is not a wrong package name, it is a syntax error, because
    parentheses are shell metacharacters.
    """
    out = []
    for b in runnable(blocks):
        for pat, why in PLACEHOLDER_PATTERNS:
            m = re.search(pat, b.body)
            if not m:
                continue
            broken = b.kind == "shell" and re.search(r"[()]", m.group(0))
            out.append(Finding(
                rule="L001",
                severity="fail" if broken else "warn",
                location=b.location(),
                summary="{} in a runnable block".format(why),
                detail="found {!r}; pasting this block {}".format(
                    m.group(0),
                    "is a shell syntax error" if broken else "runs against a literal placeholder",
                ),
            ))
            break
    return out


def check_language_tag(blocks: List[Block]) -> List[Finding]:
    """L002 - the fence says sql, the content is a shell command.

    A reader trusts the tag. pg_tde's setup page tags
    `psql -d template1 -c '...'` as sql; pasted into psql, as the tag
    instructs, it raises: syntax error at or near "psql".
    """
    out = []
    for b in runnable(blocks):
        if b.kind != "sql":
            continue
        for ln in b.lines:
            head = _first_word(strip_prompts(ln))
            if head in SHELL_HEADS and not re.match(r"^\s*(SELECT|CREATE|ALTER|DROP|INSERT|\\)", ln, re.I):
                out.append(Finding(
                    rule="L002",
                    severity="fail",
                    location=b.location(),
                    summary="block tagged '{}' contains a shell command".format(b.lang),
                    detail="line starts with {!r}; pasted into psql it raises a syntax error".format(head),
                ))
                break
    return out


def check_identifier_drift(blocks: List[Block], path: str) -> List[Finding]:
    """L003 - the page inspects an object it never created.

    Two live examples on the same doc set: a keyring page creates
    `customer_table` then tells you to run `\\d+ test1`, and a validation page
    creates `albums` then calls pg_tde_is_encrypted('table_name').
    Both leave a reader staring at "did not find any relation".

    Calibration matters more than coverage here. Three things look identical to
    a naive matcher and are not the same defect:

      1. a page that creates `customer_table` then inspects `test1`
         - a real defect, the worked example does not work
      2. a page that creates nothing and inspects `mytable`
         - not a defect, it is a fragment and the reader brings their own table
      3. a page that queries `pg_stat_replication`
         - not a defect, that is a system view, nobody creates it

    Only the first is reported as a failure. Running this uncalibrated over the
    pg_tde doc set produced eleven L003 failures, of which four were real.
    """
    created: Set[str] = set()
    out = []
    for b in runnable(blocks):
        if b.kind != "sql":
            continue
        for ident in sorted(_sql_identifiers_referenced(b.body)):
            if ident in created or ident.startswith("pg_"):
                continue  # case 3: system catalogs and views
            if not created:
                out.append(Finding(
                    rule="L003",
                    severity="note",
                    location=b.location(),
                    summary="references {!r} on a page that creates no tables".format(ident),
                    detail="reader is expected to substitute their own object; not a defect",
                ))
                continue  # case 2: a fragment, not a worked example
            out.append(Finding(
                rule="L003",
                severity="fail",
                location=b.location(),
                summary="references {!r}, but this page created {}".format(
                    ident, " and ".join(sorted(created))),
                detail="the worked example on this page does not run as written",
            ))
        created |= _sql_identifiers_created(b.body)
    return out


def check_version_drift(blocks: List[Block], expect_major: Optional[str]) -> List[Finding]:
    """L004 - a hardcoded major version that no longer matches the doc set."""
    if not expect_major:
        return []
    out = []
    for b in runnable(blocks):
        for m in re.finditer(r"\b(?:postgresql-|ppg-|percona-pg-tde)(\d{2})\b", b.body):
            if m.group(1) != expect_major:
                out.append(Finding(
                    rule="L004",
                    severity="warn",
                    location=b.location(),
                    summary="hardcoded version {} in a doc set targeting {}".format(
                        m.group(1), expect_major),
                    detail="found {!r}".format(m.group(0)),
                ))
    return out


def lint_page(text: str, path: str, expect_major: Optional[str] = None) -> List[Finding]:
    blocks = extract(text, path)
    findings: List[Finding] = []
    findings += check_placeholder_in_runnable(blocks)
    findings += check_language_tag(blocks)
    findings += check_identifier_drift(blocks, path)
    findings += check_version_drift(blocks, expect_major)
    return sorted(findings, key=lambda f: f.sort_key())
