"""Discover and score agent prompt files in a repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewscore.scoring import build_result
from crewscore.scorers import structural_analysis
from crewscore.smells import detect_smells, find_repo_root
from crewscore.profiles import classify_path

# Exact basenames always treated as agent instruction files.
KNOWN_NAMES = frozenset(
    {
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "SYSTEM.md",
        "system-prompt.md",
        "system_prompt.md",
        "system.prompt.md",
        "AGENT.md",
        "prompts.md",
        "agent-prompt.md",
        "agent_prompt.md",
    }
)

# Directory names that mark a tree as containing prompt/agent files.
# Note: bare `.cursor` is intentionally NOT listed — Cursor slash-command
# snippets under `.cursor/commands/` are not agent system prompts. Rules still
# match via the `rules` component (e.g. `.cursor/rules/*.mdc`).
PROMPT_DIR_NAMES = frozenset(
    {
        "agents",
        "prompts",
        "prompt",
        "system-prompts",
        "system_prompts",
        "rules",
    }
)

# Extensions collected under prompt/agent directories.
PROMPT_DIR_EXTENSIONS = frozenset({".md", ".txt", ".yaml", ".yml", ".mdc"})

# Directories never traversed during discovery.
# Includes local-only / generated trees documented in docs/architecture.md so a
# developer cache (e.g. .corpus-cache) cannot flood scan results.
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
        ".pytest_cache",
        "build",
        ".mypy_cache",
        ".corpus-cache",
        "test-results",
        "_production",
        "_product-experience",
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


def _is_cursor_command_noise(path: Path, root: Path) -> bool:
    """True for Cursor slash-command markdown under `.cursor/commands/`."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    parts = [p.lower() for p in relative.parts[:-1]]
    for i, part in enumerate(parts):
        if part == ".cursor" and i + 1 < len(parts) and parts[i + 1] == "commands":
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

    # Cursor command snippets are never agent system prompts, even if a known
    # basename somehow lands there.
    if _is_cursor_command_noise(path, root):
        return False

    if path.name in KNOWN_NAMES:
        return True

    # Case-insensitive known basenames (Windows-friendly + Linux clones)
    if path.name.lower() in {n.lower() for n in KNOWN_NAMES}:
        return True

    # Common *system*prompt* / *agent*prompt* patterns at any depth
    lower = path.name.lower()
    if path.suffix.lower() in {".md", ".txt"} and (
        "system-prompt" in lower
        or "system_prompt" in lower
        or lower.endswith("prompt.md")
        and "readme" not in lower
    ):
        if "system" in lower or lower.startswith("agent"):
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


def score_paths(
    paths: list[Path], *, profile: str | None = None
) -> list[dict[str, Any]]:
    """Score each path with structural analysis; return result dicts.

    Each dict has: path, overall, tier, dimensions, and optionally ruleset
    when available on the ScoreResult / module.

    `profile` forces every path onto one ruleset (the `--profile` escape hatch
    for a misclassified file). None keeps per-path classification.
    """
    results: list[dict[str, Any]] = []
    repo_roots: dict[Path, Any] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        dimensions = structural_analysis.analyze(text)
        # Repo root is per-directory, and a scan usually walks one repo —
        # cache it rather than climbing the tree once per file.
        parent = Path(path).parent
        if parent not in repo_roots:
            repo_roots[parent] = find_repo_root(path)
        result = build_result(
            dimensions,
            mode="structural",
            # `prompt_text` is what the boilerplate warning is computed from.
            # Omitting it made the `warnings` parity promised below a lie:
            # scan rows could never carry template_boilerplate_detected, and
            # scan is the CI mode the README recommends.
            prompt_text=text,
            source=str(path),
            smells=detect_smells(text, path=path, repo_root=repo_roots[parent]),
            profile=profile or classify_path(path),
        )
        item: dict[str, Any] = {
            "path": str(path),
            "tier": result.tier,
            "smells": result.smells,
            "profile": result.profile,
            "governance_applicable": result.governance_applicable,
            # `path` is rewritten to a scan-relative display path by the CLI;
            # `source` keeps the artifact the row was actually read from, and
            # `warnings` matches the shape `test --json` already emits so a
            # caller can consume either payload with the same code.
            "source": result.source,
            "warnings": result.warnings,
        }
        if result.governance_applicable:
            # Coding-agent config is judged on smells, so it publishes no
            # number and no dimension breakdown — same contract as
            # ScoreResult.to_dict() and the browser engine. Consumers must
            # branch on `governance_applicable` before reading `overall`.
            item["overall"] = result.overall
            item["dimensions"] = result.dimensions
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
