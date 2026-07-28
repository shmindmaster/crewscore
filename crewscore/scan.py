"""Discover and score agent prompt files in a repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewscore.scoring import build_result
from crewscore.scorers import structural_analysis

# Exact basenames always treated as agent instruction files.
KNOWN_NAMES = frozenset(
    {
        "AGENTS.md",
        "CLAUDE.md",
        "system-prompt.md",
        "system_prompt.md",
        "AGENT.md",
        "prompts.md",
    }
)

# Directory names that mark a tree as containing prompt/agent files.
PROMPT_DIR_NAMES = frozenset({"agents", "prompts", "prompt"})

# Extensions collected under prompt/agent directories.
PROMPT_DIR_EXTENSIONS = frozenset({".md", ".txt", ".yaml", ".yml"})

# Directories never traversed during discovery.
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "__pycache__",
        ".tox",
        "site-packages",
    }
)

MAX_FILE_BYTES = 500 * 1024
# Max directory depth relative to the scan root (root = 0).
MAX_DEPTH = 8


def _is_under_prompt_dir(path: Path, root: Path) -> bool:
    """True if any path component between root and file is a prompt dir name."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    # Check parent directory names only (not the file itself).
    for part in relative.parts[:-1]:
        if part.lower() in PROMPT_DIR_NAMES:
            return True
    return False


def _should_include(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False

    if path.name in KNOWN_NAMES:
        return True

    if _is_under_prompt_dir(path, root) and path.suffix.lower() in PROMPT_DIR_EXTENSIONS:
        return True

    return False


def discover_prompt_files(root: Path) -> list[Path]:
    """Find likely agent instruction / system-prompt files under root.

    Discovers:
    - Known basenames (AGENTS.md, CLAUDE.md, system-prompt.md, …)
    - Files under directories named agents / prompts / prompt with
      extensions .md, .txt, .yaml, .yml

    Skips excluded directories, files larger than 500KB, and depth beyond
    MAX_DEPTH. Returns sorted unique absolute paths.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        return []

    found: set[Path] = set()

    def _walk(current: Path, depth: int) -> None:
        if depth > MAX_DEPTH:
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
                    # Also skip hidden dirs other than those we might care about?
                    # Spec only lists explicit skip set — do not skip all hidden.
                    _walk(entry, depth + 1)
                elif entry.is_file():
                    if _should_include(entry, root):
                        found.add(entry.resolve())
            except OSError:
                continue

    _walk(root, depth=0)
    return sorted(found)


def score_paths(paths: list[Path]) -> list[dict[str, Any]]:
    """Score each path with structural analysis; return result dicts.

    Each dict has: path, overall, tier, dimensions, and optionally ruleset
    when available on the ScoreResult / module.
    """
    results: list[dict[str, Any]] = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        dimensions = structural_analysis.analyze(text)
        result = build_result(dimensions, mode="structural", source=str(path))
        item: dict[str, Any] = {
            "path": str(path),
            "overall": result.overall,
            "tier": result.tier,
            "dimensions": result.dimensions,
        }
        # Include ruleset when workstream A has shipped it.
        ruleset = getattr(result, "ruleset", None)
        if ruleset is None:
            try:
                from crewscore import scoring as scoring_mod

                ruleset = getattr(scoring_mod, "RULESET_ID", None)
            except Exception:
                ruleset = None
        if ruleset is not None:
            item["ruleset"] = ruleset
        results.append(item)
    return results
