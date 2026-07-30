"""Tests for offline extraction of system-prompt string literals in source."""

from __future__ import annotations

from pathlib import Path

from crewscore.extract_inline import (
    InlinePrompt,
    discover_inline_prompts,
    extract_inline_prompts,
)
from crewscore.scan import score_inline_prompts

# Long enough to clear the 80-char MIN after strip.
LONG_PROMPT = (
    "You are a helpful production assistant that answers carefully and "
    "follows the user's instructions without revealing internal policy."
)
assert len(LONG_PROMPT.strip()) >= 80


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_extract_python_triple_quoted_system_prompt(tmp_path: Path):
    """SYSTEM_PROMPT = \"\"\"...\"\"\" is extracted from a .py file."""
    src = _write(
        tmp_path / "src" / "agent.py",
        f'SYSTEM_PROMPT = """{LONG_PROMPT}"""\n',
    )
    found = extract_inline_prompts(src)
    assert len(found) == 1
    item = found[0]
    assert isinstance(item, InlinePrompt)
    assert item.path == src.resolve() or item.path == src
    assert item.name == "SYSTEM_PROMPT"
    assert item.line == 1
    assert item.text == LONG_PROMPT
    assert item.display_path.endswith("agent.py:SYSTEM_PROMPT")
    assert "src" in item.display_path.replace("\\", "/")


def test_extract_ts_template_literal_system_prompt(tmp_path: Path):
    """const SYSTEM_PROMPT = `...` is extracted from a .ts file."""
    src = _write(
        tmp_path / "bot.ts",
        f"const SYSTEM_PROMPT = `{LONG_PROMPT}`;\n",
    )
    found = extract_inline_prompts(src)
    assert len(found) == 1
    assert found[0].name == "SYSTEM_PROMPT"
    assert found[0].text == LONG_PROMPT
    assert found[0].display_path.endswith("bot.ts:SYSTEM_PROMPT")


def test_reject_short_strings(tmp_path: Path):
    """Assignments shorter than 80 chars after strip are ignored."""
    short = "You are a short prompt."
    assert len(short.strip()) < 80
    src = _write(
        tmp_path / "short.py",
        f'SYSTEM_PROMPT = """{short}"""\n',
    )
    assert extract_inline_prompts(src) == []


def test_reject_unrelated_variable_names(tmp_path: Path):
    """Only allowlisted prompt variable names are extracted."""
    body = "x" * 100
    src = _write(
        tmp_path / "keys.py",
        f'API_KEY = "{body}"\nSECRET = "{body}"\n',
    )
    assert extract_inline_prompts(src) == []


def test_discover_skips_node_modules(tmp_path: Path):
    """discover_inline_prompts does not walk node_modules."""
    _write(
        tmp_path / "node_modules" / "pkg" / "index.js",
        f"const SYSTEM_PROMPT = `{LONG_PROMPT}`;\n",
    )
    real = _write(
        tmp_path / "app" / "agent.py",
        f'SYSTEM_PROMPT = """{LONG_PROMPT}"""\n',
    )
    found = discover_inline_prompts(tmp_path)
    assert len(found) == 1
    assert found[0].path.resolve() == real.resolve()
    assert all("node_modules" not in str(p.path) for p in found)


def test_score_inline_prompts_bare_text_overall_zero(tmp_path: Path):
    """Bare helpful-assistant text scores overall 0 via score_inline_prompts."""
    bare = (
        "You are a helpful assistant that answers questions clearly and "
        "politely for the end user of this application."
    )
    assert len(bare.strip()) >= 80
    src = _write(
        tmp_path / "agent.py",
        f'SYSTEM_PROMPT = """{bare}"""\n',
    )
    inlines = extract_inline_prompts(src)
    assert len(inlines) == 1
    rows = score_inline_prompts(inlines)
    assert len(rows) == 1
    row = rows[0]
    assert row["overall"] == 0
    assert row["path"] == inlines[0].display_path
    assert "SYSTEM_PROMPT" in row["source"]
    assert ":L" in row["source"]
    assert row["governance_applicable"] is True
    assert row["profile"] == "system_prompt"
