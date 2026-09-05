"""assay - execute the documentation, find out what is still true."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

from . import __version__
from .lint import lint_page
from .report import render_lint, render_run, to_json
from .run import Container, RunResult, run_page


def _load_manifest(path: str) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        sys.exit("assay: PyYAML is required to read a manifest (pip install pyyaml)")
    with open(path) as fh:
        return yaml.safe_load(fh)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def cmd_lint(args) -> int:
    paths: List[str] = []
    for target in args.paths:
        if os.path.isdir(target):
            for root, _, files in os.walk(target):
                paths += [os.path.join(root, f) for f in sorted(files) if f.endswith(".md")]
        else:
            paths.append(target)

    findings = []
    for p in paths:
        findings += lint_page(_read(p), p, expect_major=args.expect_major)

    if args.json:
        print(to_json(findings=findings))
    else:
        print(render_lint(findings, "{} page{}".format(
            len(paths), "" if len(paths) == 1 else "s"), color=not args.no_color))
    return 1 if any(f.severity == "fail" for f in findings) else 0


def cmd_run(args) -> int:
    manifest = _load_manifest(args.manifest)
    base = os.path.dirname(os.path.abspath(args.manifest))
    docs_root = os.path.join(base, manifest.get("docs_root", "."))
    env = manifest.get("environment", {})

    result = RunResult(image=env.get("image", "ubuntu:24.04"))
    with Container(env["image"], platform=env.get("platform")) as box:
        for line in env.get("preflight", []):
            box.sh(line)
        for page in manifest.get("pages", []):
            path = os.path.join(docs_root, page["path"])
            result.steps += run_page(
                box, page["path"], _read(path),
                substitutions=page.get("substitutions", env.get("substitutions", [])),
                skip_lines=page.get("skip", []),
            )

    result.attribute_cascades()

    if args.json:
        print(to_json(result=result))
    else:
        print(render_run(result, color=not args.no_color))
    return 1 if result.defects else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="assay",
        description="Execute the documentation. Find out what is still true.",
    )
    parser.add_argument("--version", action="version", version="assay " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="static checks, no container required")
    lint.add_argument("paths", nargs="+", help="Markdown files or directories")
    lint.add_argument("--expect-major", help="major version this doc set targets, e.g. 18")
    lint.add_argument("--json", action="store_true")
    lint.add_argument("--no-color", action="store_true")
    lint.set_defaults(func=cmd_lint)

    run = sub.add_parser("run", help="execute a documentation path in a container")
    run.add_argument("manifest", help="path to an assay manifest")
    run.add_argument("--json", action="store_true")
    run.add_argument("--no-color", action="store_true")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
