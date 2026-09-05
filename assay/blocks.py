"""Extract runnable code blocks from MkDocs Material Markdown.

The awkward part of this file is that MkDocs Material does not write plain
fenced blocks. A page can carry any of these, and all of them are the same
thing to a reader who is going to select the text and paste it:

    ```sql
    ```{.bash data-prompt="$"}
    ``` { .bash .no-copy }

Blocks are also nested inside admonitions and numbered list items, which means
the fence is indented and the content carries that indent. A naive splitter
returns SQL with four leading spaces, which then fails for reasons that have
nothing to do with the documentation being wrong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

FENCE_RE = re.compile(
    r"""^(?P<indent>[ \t]*)          # fences inside list items are indented
        (?P<fence>`{3,}|~{3,})       # ``` or ~~~, three or more
        [ \t]*
        (?P<info>[^\n]*)$            # the info string, in any of its dialects
    """,
    re.VERBOSE,
)

# ```{.bash data-prompt="$"} and ``` { .bash .no-copy } both mean "bash".
BRACE_LANG_RE = re.compile(r"\.([A-Za-z0-9_+-]+)")

# A shell prompt Material renders but a reader does not paste.
PROMPT_RE = re.compile(r"^\s*(?:\$|#|postgres=#|\w+=#)\s+")

SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "text"}
SQL_LANGS = {"sql", "psql", "postgresql"}
IGNORED_LANGS = {"ini", "yaml", "yml", "json", "conf", "diff", "output", ""}


@dataclass
class Block:
    """One fenced code block, located precisely enough to file a bug about."""

    path: str
    line: int  # 1-indexed line of the opening fence
    lang: str
    body: str
    info: str = ""
    in_admonition: bool = False

    @property
    def kind(self) -> str:
        if self.lang in SQL_LANGS:
            return "sql"
        if self.lang in SHELL_LANGS:
            return "shell"
        return "other"

    @property
    def lines(self) -> List[str]:
        return [ln for ln in self.body.splitlines() if ln.strip()]

    def location(self) -> str:
        return "{}:{}".format(self.path, self.line)


def _normalize_lang(info: str) -> str:
    """Reduce any of Material's info-string dialects to a bare language name."""
    info = info.strip()
    if not info:
        return ""
    if info.startswith("{"):
        m = BRACE_LANG_RE.search(info)
        return m.group(1).lower() if m else ""
    # ```sql title="..."  -> sql
    return info.split()[0].strip("{}").lstrip(".").lower()


def _dedent(body: str, indent: str) -> str:
    """Strip the fence's own indentation, and nothing more."""
    if not indent:
        return body
    out = []
    for ln in body.splitlines():
        out.append(ln[len(indent):] if ln.startswith(indent) else ln.lstrip())
    return "\n".join(out)


def strip_prompts(body: str) -> str:
    """Remove rendered shell prompts so the block can actually be executed.

    Material's data-prompt="$" adds the prompt at render time, but plenty of
    pages also hard-code it in the source. Both reach the reader's clipboard
    the same way.
    """
    return "\n".join(PROMPT_RE.sub("", ln) for ln in body.splitlines())


def extract(text: str, path: str) -> List[Block]:
    """Return every fenced block in `text`, in document order."""
    blocks: List[Block] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence, info = m.group("indent"), m.group("fence"), m.group("info")
        if info.strip().startswith(fence[0]):  # not an opening fence
            i += 1
            continue
        start = i
        body_lines: List[str] = []
        i += 1
        while i < len(lines):
            close = FENCE_RE.match(lines[i])
            if close and close.group("fence")[0] == fence[0] and not close.group("info").strip():
                break
            body_lines.append(lines[i])
            i += 1
        # An admonition or a ??? example wraps sample output, not instructions.
        context = "\n".join(lines[max(0, start - 4):start])
        in_adm = bool(re.search(r"^\s*(?:!!!|\?\?\?)\s", context, re.M))
        blocks.append(
            Block(
                path=path,
                line=start + 1,
                lang=_normalize_lang(info),
                body=_dedent("\n".join(body_lines), indent),
                info=info.strip(),
                in_admonition=in_adm,
            )
        )
        i += 1
    return blocks


def runnable(blocks: List[Block]) -> Iterator[Block]:
    """Blocks a reader would actually copy and run.

    Sample output inside `??? example` is excluded: it is there to be compared
    against, not executed.
    """
    for b in blocks:
        if b.kind == "other":
            continue
        if b.in_admonition and re.search(r"row\)|^-{3,}$", b.body, re.M):
            continue
        if not b.body.strip():
            continue
        yield b
