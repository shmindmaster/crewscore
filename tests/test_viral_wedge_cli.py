"""CLI integration for viral-wedge surfaces: inline extract, hero, coverage."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main

LONG_BARE = (
    "You are a helpful assistant that answers user questions about the product "
    "and helps them complete workflows in the application."
)


def test_test_json_includes_coverage_and_hero():
    runner = CliRunner()
    result = runner.invoke(
        main, ["test", "--prompt", "You are a helpful assistant.", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["governance_applicable"] is True
    cov = payload["coverage"]
    assert cov["total"] == 23
    assert cov["matched"] == 0
    assert cov["hero"]["concept"] == "human_gate.approval_required"


def test_test_human_shows_control_coverage_and_hero_gap():
    runner = CliRunner()
    result = runner.invoke(
        main, ["test", "--prompt", "You are a helpful assistant."]
    )
    assert result.exit_code == 0, result.output
    assert "CONTROL COVERAGE:" in result.output
    assert "0/23" in result.output
    assert "FIRST GAP TO REVIEW:" in result.output
    assert "human must approve" in result.output.lower() or "A human must approve" in result.output
    assert "--require human_gate.approval_required" in result.output
    assert "Control coverage" in result.output or "CONTROL COVERAGE" in result.output


def test_scan_finds_inline_system_prompt(tmp_path: Path):
    src = tmp_path / "app"
    src.mkdir()
    (src / "agent.py").write_text(
        "SYSTEM_PROMPT = \"\"\"\n" + LONG_BARE + "\n\"\"\"\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload) >= 1
    paths = [row["path"] for row in payload]
    assert any("SYSTEM_PROMPT" in p for p in paths)
    governed = [r for r in payload if r.get("governance_applicable")]
    assert governed
    assert "coverage" in governed[0]
    assert governed[0]["coverage"]["total"] == 23
    assert governed[0]["coverage"]["hero"]["concept"] == "human_gate.approval_required"


def test_scan_no_inline_skips_source_literals(tmp_path: Path):
    (tmp_path / "agent.py").write_text(
        "SYSTEM_PROMPT = \"\"\"\n" + LONG_BARE + "\n\"\"\"\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--json", "--no-inline"])
    assert result.exit_code == 1
    assert result.output.strip() == "[]"


def test_scan_human_shows_hero_when_inline_present(tmp_path: Path):
    (tmp_path / "bot.py").write_text(
        "system_prompt = \"\"\"\n" + LONG_BARE + "\n\"\"\"\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "FIRST GAP TO REVIEW:" in result.output
    assert "--require human_gate.approval_required" in result.output
    assert "Coverage" in result.output or "coverage" in result.output.lower()
