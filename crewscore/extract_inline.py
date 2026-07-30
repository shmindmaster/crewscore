"""Offline extraction of system-prompt string literals embedded in source code.

Finds assignments to known prompt variable names in Python / JS / TS files and
returns the string bodies for structural scoring. Pattern match only — not AST
proof of runtime behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from crewscore.scan import MAX_DEPTH, MAX_FILE_BYTES, SKIP_DIRS

# Exact names only (case-sensitive). Callers burying prompts under other names
# are out of scope for this offline extractor.
PROMPT_NAMES: tuple[str, ...] = (
    "system_prompt",
    "SYSTEM_PROMPT",
    "agent_prompt",
    "AGENT_PROMPT",
    "agent_system_prompt",
    "SYSTEM_MESSAGE",
    "system_message",
    "DEFAULT_SYSTEM_PROMPT",
)

SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
)

MIN_PROMPT_CHARS = 80
MAX_PROMPT_CHARS = 100_000

_NAME_ALT = "|".join(re.escape(n) for n in PROMPT_NAMES)

# Optional JS/TS binding keywords, optional type annotation, then = string.
# Quote alternatives ordered longest-first so """ wins over ".
_ASSIGN_RE = re.compile(
    rf"""
    (?:(?:export\s+)?(?:const|let|var)\s+)?   # JS/TS binding
    (?P<name>{_NAME_ALT})
    (?:\s*:\s*[^=\n]+)?                       # optional type annotation
    \s*=\s*
    (?P<quote>\"\"\"|'''|`|\"|')
    (?P<body>.*?)
    (?P=quote)
    """,
    re.VERBOSE | re.DOTALL,
)


@dataclass
class InlinePrompt:
    """One system-prompt string literal found in a source file."""

    path: Path
    name: str
    line: int
    text: str
    display_path: str  # e.g. src/agent.py:SYSTEM_PROMPT


def _relative_display(path: Path, name: str, root: Path | None = None) -> str:
    """Build posix-ish `rel/path:NAME` when a root (or cwd) makes that possible."""
    resolved = Path(path).resolve()
    bases: list[Path] = []
    if root is not None:
        bases.append(Path(root).resolve())
    bases.append(Path.cwd())
    rel_str: str | None = None
    for base in bases:
        try:
            rel_str = resolved.relative_to(base).as_posix()
            break
        except ValueError:
            continue
    if rel_str is None:
        rel_str = Path(path).as_posix()
    return f"{rel_str}:{name}"


def extract_inline_prompts(path: Path, *, root: Path | None = None) -> list[InlinePrompt]:
    """Extract allowlisted prompt-variable string literals from one source file."""
    path = Path(path)
    if path.suffix.lower() not in SOURCE_EXTENSIONS:
        return []
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
    except OSError:
        return []

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    found: list[InlinePrompt] = []
    for match in _ASSIGN_RE.finditer(source):
        body = match.group("body")
        text = body.strip()
        if len(text) < MIN_PROMPT_CHARS:
            continue
        if len(text) > MAX_PROMPT_CHARS:
            continue
        name = match.group("name")
        line = source.count("\n", 0, match.start()) + 1
        found.append(
            InlinePrompt(
                path=path.resolve(),
                name=name,
                line=line,
                text=text,
                display_path=_relative_display(path, name, root=root),
            )
        )
    return found


def discover_inline_prompts(
    root: Path, *, max_depth: int = MAX_DEPTH
) -> list[InlinePrompt]:
    """Walk a tree and extract inline prompts from supported source files.

    Skips the same directories as ``scan.SKIP_DIRS`` and files larger than
    ``scan.MAX_FILE_BYTES``. Depth is measured relative to root (root = 0).
    """
    root = Path(root).resolve()
    if not root.is_dir():
        return []

    found: list[InlinePrompt] = []

    def _walk(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(current.iterdir())
        except OSError:
            return
        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in SKIP_DIRS:
                        continue
                    _walk(entry, depth + 1)
                elif entry.is_file() and entry.suffix.lower() in SOURCE_EXTENSIONS:
                    found.extend(extract_inline_prompts(entry, root=root))
            except OSError:
                continue

    _walk(root, depth=0)
    # Stable order: by display path then line.
    found.sort(key=lambda p: (p.display_path, p.line, p.name))
    return found
