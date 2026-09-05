"""Report rendering. Terminal by default, JSON when something else has to read it."""

from __future__ import annotations

import json
from typing import List, Optional

from .lint import Finding
from .run import RunResult, Step

RESET = "\033[0m"
COLORS = {
    "fail": "\033[31m", "warn": "\033[33m", "note": "\033[36m",
    "pass": "\033[32m", "adapted": "\033[35m", "skipped": "\033[90m",
    "blocked": "\033[90m",
    "dim": "\033[90m", "bold": "\033[1m",
}


def _c(text: str, key: str, color: bool) -> str:
    return "{}{}{}".format(COLORS[key], text, RESET) if color and key in COLORS else text


def _indent(text: str, prefix: str = "      ", limit: int = 6) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()][:limit]
    return "\n".join(prefix + ln for ln in lines)


def render_lint(findings: List[Finding], source: str, color: bool = True) -> str:
    out = ["", _c("assay lint", "bold", color) + "  " + _c(source, "dim", color), ""]
    if not findings:
        out.append("  no static findings")
        out.append("")
        return "\n".join(out)

    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = "  ".join(
        "{} {}".format(_c(sev.upper(), sev, color), counts[sev])
        for sev in ("fail", "warn", "note") if sev in counts
    )
    out.append("  " + summary)
    out.append("")
    for f in findings:
        out.append("  {} {}  {}".format(
            _c(f.severity.upper().ljust(4), f.severity, color),
            _c(f.rule, "dim", color),
            f.location,
        ))
        out.append("       {}".format(f.summary))
        if f.detail:
            out.append("       {}".format(_c(f.detail, "dim", color)))
        out.append("")
    return "\n".join(out)


def render_run(result: RunResult, color: bool = True) -> str:
    c = result.counts()
    out = [
        "",
        _c("assay run", "bold", color) + "  " + _c(result.image, "dim", color),
        "",
        "  {}  {}   {}  {}   {}  {}   {}  {}   {}  {}".format(
            _c("PASS", "pass", color), c["pass"],
            _c("FAIL", "fail", color), c["fail"],
            _c("BLOCKED", "blocked", color), c["blocked"],
            _c("ADAPTED", "adapted", color), c["adapted"],
            _c("SKIPPED", "skipped", color), c["skipped"],
        ),
        "",
    ]

    if c["adapted"]:
        out.append("  " + _c("Adapted commands are harness limitations, not doc defects:", "dim", color))
        for s in result.steps:
            if s.status == "adapted":
                out.append("    {}  {}".format(_c(s.block.location(), "dim", color), s.note))
        out.append("")

    for s in result.defects:
        out.append("  {}  {}".format(_c("FAIL", "fail", color), s.block.location()))
        out.append("       $ {}".format(s.command.splitlines()[0][:100]))
        out.append("       exit {}".format(s.exit_code))
        if s.output:
            out.append(_c(_indent(s.output), "dim", color))
        out.append("")

    blocked = [s for s in result.steps if s.status == "blocked"]
    if blocked:
        by = blocked[0].blocked_by
        out.append("  " + _c(
            "{} further command{} could not run; all blocked by {}".format(
                len(blocked), "" if len(blocked) == 1 else "s", by), "dim", color))
        out.append("  " + _c(
            "They are downstream of one root cause, not separate defects.", "dim", color))
        out.append("")

    verdict = "{} documentation defect{}".format(
        len(result.defects), "" if len(result.defects) == 1 else "s")
    out.append("  " + (_c(verdict + " -> exit 1", "fail", color)
                       if result.defects else _c("chain intact -> exit 0", "pass", color)))
    out.append("")
    return "\n".join(out)


def to_json(findings: Optional[List[Finding]] = None,
            result: Optional[RunResult] = None) -> str:
    payload = {}
    if findings is not None:
        payload["lint"] = [f.__dict__ for f in findings]
    if result is not None:
        payload["run"] = {
            "image": result.image,
            "counts": result.counts(),
            "steps": [
                {
                    "location": s.block.location(),
                    "status": s.status,
                    "exit_code": s.exit_code,
                    "command": s.command,
                    "output": s.output,
                    "note": s.note,
                    "blocked_by": s.blocked_by,
                }
                for s in result.steps
            ],
        }
    return json.dumps(payload, indent=2)
