"""Discovery must stay inside the caller-selected scan root (SH-2708).

Covers symlinked files, symlinked directories, link cycles, broken links, and
plain in-root traversal. Link-dependent cases probe for the primitive at
runtime and skip when the platform cannot create it.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from crewscore.cli import main
from crewscore.extract_inline import discover_inline_prompts
from crewscore.pathsafe import (
    REASON_BROKEN_LINK,
    REASON_OUTSIDE_ROOT,
    REASON_SYMLINKED_DIR,
    REASON_UNRESOLVABLE_LINK,
    SKIP,
    SkippedPath,
    classify_entry,
    is_within,
    resolve_root,
)
from crewscore.profiles import CODING_AGENT_CONFIG, SYSTEM_PROMPT
from crewscore.scan import discover_prompt_files, score_paths

BARE = "You are a helpful assistant."
INLINE_SOURCE = (
    'SYSTEM_PROMPT = """You are a helpful assistant that always answers '
    'with a short paragraph and never invents facts or sources."""\n'
)


def _write(path: Path, text: str = BARE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _symlink(target: Path, link: Path) -> None:
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        # Windows needs to be told the target is a directory before it will
        # create a directory link.
        os.symlink(target, link, target_is_directory=Path(target).is_dir())


def _symlink_supported() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target.txt"
        target.write_text("x", encoding="utf-8")
        link = root / "link.txt"
        try:
            _symlink(target, link)
        except (OSError, NotImplementedError, AttributeError):
            return False
        return link.is_symlink()


CAN_SYMLINK = _symlink_supported()

needs_symlink = pytest.mark.skipif(
    not CAN_SYMLINK,
    reason="os.symlink unavailable (Windows without developer mode or elevation)",
)


# ---------------------------------------------------------------------------
# platform-independent: containment is pure path reasoning
# ---------------------------------------------------------------------------


def test_helper_rejects_path_resolving_outside_root(tmp_path: Path):
    """The helper rejects anything that does not resolve under the root."""
    root = resolve_root(tmp_path / "scan-root")
    root.mkdir()
    inside = _write(root / "AGENTS.md")
    outside = _write(tmp_path / "elsewhere" / "system-prompt.md")

    assert is_within(inside, root) is True
    assert is_within(outside, root) is False
    assert is_within(root.parent, root) is False
    # A sibling whose name merely starts with the root name is still outside.
    assert is_within(tmp_path / "scan-root-archive" / "AGENTS.md", root) is False

    action, reason = classify_entry(outside, root)
    assert action == SKIP
    assert reason == REASON_OUTSIDE_ROOT


def test_helper_reads_plain_in_root_entries(tmp_path: Path):
    """Ordinary files and directories inside the root are not refused."""
    root = resolve_root(tmp_path)
    _write(root / "system-prompt.md")
    (root / "nested").mkdir()

    assert classify_entry(root / "system-prompt.md", root)[0] == "read"
    assert classify_entry(root / "nested", root) == ("descend", None)


def test_in_root_traversal_and_classification_unchanged(tmp_path: Path):
    """A plain in-root tree is discovered, ordered and classified as before."""
    root = resolve_root(tmp_path)
    agents = _write(root / "AGENTS.md")
    _write(root / "CLAUDE.md")
    prompt_dir_file = _write(root / "prompts" / "one.md")
    deep = _write(root / "src" / "deep" / "system-prompt.md")
    _write(root / "README.md")
    _write(root / "notes.txt")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert skipped == []
    # sorted unique absolute paths, unchanged ordering
    assert found == sorted([agents, root / "CLAUDE.md", prompt_dir_file, deep])
    assert {p.name for p in found} == {
        "AGENTS.md",
        "CLAUDE.md",
        "one.md",
        "system-prompt.md",
    }

    by_path = {item["path"]: item for item in score_paths(found)}
    assert by_path[str(agents)]["profile"] == CODING_AGENT_CONFIG
    assert by_path[str(agents)]["governance_applicable"] is False
    assert by_path[str(deep)]["profile"] == SYSTEM_PROMPT
    assert by_path[str(deep)]["governance_applicable"] is True


# ---------------------------------------------------------------------------
# link escapes
# ---------------------------------------------------------------------------


@needs_symlink
def test_symlinked_file_outside_root_is_not_read(tmp_path: Path):
    """A symlink inside the root pointing at a file outside is not opened."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    outside_prompt = _write(outside / "system-prompt.md", "SECRET OUTSIDE TEXT")
    _write(root / "AGENTS.md")
    _symlink(outside_prompt, root / "linked-prompt.md")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert outside_prompt.resolve() not in {p.resolve() for p in found}
    assert [p.name for p in found] == ["AGENTS.md"]
    reasons = {item.reason for item in skipped}
    assert reasons & {REASON_OUTSIDE_ROOT, "symlinked_file_not_followed"}
    assert "SECRET OUTSIDE TEXT" not in "".join(
        p.read_text(encoding="utf-8") for p in found
    )


@needs_symlink
def test_symlinked_directory_outside_root_is_not_descended(tmp_path: Path):
    """A symlinked directory pointing outside the root is never walked into."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    outside_prompt = _write(outside / "system-prompt.md", "SECRET OUTSIDE TEXT")
    _write(root / "AGENTS.md")
    _symlink(outside, root / "linked-dir")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert outside_prompt.resolve() not in {p.resolve() for p in found}
    assert [p.name for p in found] == ["AGENTS.md"]
    assert {item.reason for item in skipped} & {
        REASON_OUTSIDE_ROOT,
        REASON_SYMLINKED_DIR,
    }


@needs_symlink
def test_symlinked_directory_inside_root_is_still_not_followed(tmp_path: Path):
    """Fail closed: an in-root directory link is skipped, not descended."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    real = root / "real"
    real.mkdir()
    _write(real / "system-prompt.md")
    _symlink(real, root / "alias")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert [p.name for p in found] == ["system-prompt.md"]
    assert [item.reason for item in skipped] == [REASON_SYMLINKED_DIR]


@needs_symlink
def test_directory_link_cycle_terminates(tmp_path: Path):
    """Self- and mutually-referential directory links neither hang nor crash."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    _write(root / "AGENTS.md")
    _symlink(root / "self", root / "self")
    _symlink(root / "b", root / "a")
    _symlink(root / "a", root / "b")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert [p.name for p in found] == ["AGENTS.md"]
    assert skipped
    for item in skipped:
        assert item.reason in {REASON_BROKEN_LINK, REASON_UNRESOLVABLE_LINK}


@needs_symlink
def test_broken_link_is_skipped_without_raising(tmp_path: Path):
    """A dangling link is reported, never opened, never fatal."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    _write(root / "AGENTS.md")
    _symlink(tmp_path / "does-not-exist" / "system-prompt.md", root / "dangling.md")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert [p.name for p in found] == ["AGENTS.md"]
    assert [item.reason for item in skipped] == [REASON_BROKEN_LINK]


@needs_symlink
def test_ignored_directory_link_is_not_reported_as_unsafe(tmp_path: Path):
    """SKIP_DIRS names stay silent: they are excluded by rule, not by safety."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    _write(root / "AGENTS.md")
    outside_prompts = tmp_path / "outside-node-modules"
    _write(outside_prompts / "system-prompt.md")
    _symlink(outside_prompts, root / "node_modules")

    skipped: list[SkippedPath] = []
    found = discover_prompt_files(root, skipped=skipped)

    assert [p.name for p in found] == ["AGENTS.md"]
    assert skipped == []


@needs_symlink
def test_inline_discovery_uses_the_same_containment(tmp_path: Path):
    """Inline extraction refuses the same escapes as file discovery."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    _write(outside / "agent.py", INLINE_SOURCE)
    _write(root / "agent.py", INLINE_SOURCE)
    _symlink(outside, root / "linked-dir")

    skipped: list[SkippedPath] = []
    found = discover_inline_prompts(root, skipped=skipped)

    assert [p.display_path for p in found] == ["agent.py:SYSTEM_PROMPT"]
    assert skipped


# ---------------------------------------------------------------------------
# CLI output contract
# ---------------------------------------------------------------------------


def test_json_empty_scan_has_no_skip_signal(tmp_path: Path):
    """A genuinely empty root reports nothing but the empty array."""
    root = resolve_root(tmp_path / "empty")
    root.mkdir()

    result = CliRunner().invoke(main, ["scan", str(root), "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == []
    assert "skipped_unsafe_path" not in result.stderr


@needs_symlink
def test_json_reports_skipped_unsafe_paths_on_stderr(tmp_path: Path):
    """`--json` keeps stdout pure and still marks a scan that refused links."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    _write(outside / "system-prompt.md")
    _symlink(outside / "system-prompt.md", root / "linked-prompt.md")

    result = CliRunner().invoke(main, ["scan", str(root), "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == []
    alerts = [
        json.loads(line)
        for line in result.stderr.splitlines()
        if line.startswith("{") and line.endswith("}")
    ]
    assert any("skipped_unsafe_path" in alert for alert in alerts)
    # File discovery and inline extraction walk the same tree; one report each.
    reported = [
        alert["skipped_unsafe_path"]["path"]
        for alert in alerts
        if "skipped_unsafe_path" in alert
    ]
    assert reported.count(str(root / "linked-prompt.md")) == 1
    assert "skipped as unsafe" in result.stderr


@needs_symlink
def test_human_output_reports_skipped_unsafe_paths(tmp_path: Path):
    """The console path names each refused path and why."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    _write(outside / "system-prompt.md")
    _symlink(outside, root / "linked-dir")

    result = CliRunner().invoke(main, ["scan", str(root)])

    assert result.exit_code == 1
    assert "Skipped" in result.stderr
    assert "skipped as unsafe" in result.stderr


@needs_symlink
def test_oversized_and_unsafe_skips_are_both_reported(tmp_path: Path):
    """The two skip channels do not clobber each other."""
    root = resolve_root(tmp_path / "repo")
    root.mkdir()
    outside = tmp_path / "outside"
    _write(outside / "system-prompt.md")
    _symlink(outside / "system-prompt.md", root / "linked-prompt.md")
    _write(root / "system-prompt.md", "x" * (500 * 1024 + 1))

    result = CliRunner().invoke(main, ["scan", str(root)])

    assert result.exit_code == 1
    assert "larger than 500KB" in result.stderr
    assert "skipped as unsafe" in result.stderr


def test_scan_json_row_keys_stable(tmp_path: Path):
    """Containment does not change the established per-row key set."""
    root = resolve_root(tmp_path)
    _write(root / "AGENTS.md")
    _write(root / "system-prompt.md")

    result = CliRunner().invoke(main, ["scan", str(root), "--json"])

    assert result.exit_code == 0, result.stderr
    rows = json.loads(result.stdout)
    assert isinstance(rows, list)
    assert len(rows) == 2
    for row in rows:
        assert {
            "path",
            "tier",
            "smells",
            "profile",
            "governance_applicable",
            "source",
            "warnings",
            "ruleset",
        } <= set(row)
    governed = [row for row in rows if row["governance_applicable"]]
    assert governed and "overall" in governed[0]
    assert "overall" not in next(
        row for row in rows if not row["governance_applicable"]
    )
