"""CLI contract tests for CrewScore."""

import json
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main

BARE = "You are a helpful assistant."


def test_test_json_output():
    runner = CliRunner()
    result = runner.invoke(main, ["test", "--prompt", BARE, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "overall" in payload
    assert "dimensions" in payload
    assert payload["mode"] == "structural"
    assert len(payload["dimensions"]) == 8
    from crewscore.scoring import RULESET_ID

    assert payload["ruleset"] == RULESET_ID
    assert isinstance(payload["warnings"], list)
    assert payload["tier"].startswith("STRUCTURAL:")


def test_test_json_template_warning_after_fix(tmp_path: Path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    runner.invoke(
        main,
        ["fix", "--prompt-file", str(prompt_file), "--apply", "--json"],
    )
    result = runner.invoke(
        main, ["test", "--prompt-file", str(prompt_file), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "template_boilerplate_detected" in payload["warnings"]


def test_test_threshold_fails():
    runner = CliRunner()
    result = runner.invoke(
        main, ["test", "--prompt", BARE, "--json", "--threshold", "50"]
    )
    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["overall"] < 50


def test_test_threshold_human_mode_no_crash():
    """Human-mode threshold must exit 2 cleanly (no Rich Console TypeError)."""
    runner = CliRunner()
    result = runner.invoke(main, ["test", "--prompt", BARE, "--threshold", "50"])
    assert result.exit_code == 2
    assert not isinstance(result.exception, TypeError)
    assert "Threshold failure" in result.output
    assert "TypeError" not in result.output


def test_test_requires_input():
    runner = CliRunner()
    result = runner.invoke(main, ["test"])
    assert result.exit_code == 1
    assert not isinstance(result.exception, TypeError)
    assert "Provide --prompt" in result.output
    assert "TypeError" not in result.output


def test_fix_requires_input():
    runner = CliRunner()
    result = runner.invoke(main, ["fix"])
    assert result.exit_code == 1
    assert not isinstance(result.exception, TypeError)
    assert "Provide --prompt" in result.output


def test_assess_vendor_bad_answer_count():
    runner = CliRunner()
    result = runner.invoke(
        main, ["assess-vendor", "--name", "Acme", "--answers", "y,n"]
    )
    assert result.exit_code == 1
    assert not isinstance(result.exception, TypeError)
    assert "Expected 10 answers" in result.output


def test_fix_json_raises_score(tmp_path: Path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["fix", "--prompt-file", str(prompt_file), "--apply", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["after"]["overall"] > payload["before"]["overall"]
    assert payload["fixes_applied"]
    assert "Guardrails" in prompt_file.read_text(encoding="utf-8")
    assert "CrewScore" in prompt_file.read_text(encoding="utf-8")


def test_assess_vendor_json():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "assess-vendor",
            "--name",
            "Acme AI",
            "--answers",
            "y,y,n,dk,y,y,n,y,n,y",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["vendor"] == "Acme AI"
    assert payload["score"] == 10 * 6 + 3 * 1 + 0 * 3  # 6 yes, 1 dk, 3 no
    assert len(payload["answers"]) == 10


def test_fix_mentions_runtime_gates():
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--prompt", "You are helpful."])
    assert result.exit_code == 0
    assert "runtime" in result.output.lower()


def test_fix_json_includes_honesty_note():
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--prompt", "You are helpful.", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    note = payload.get("note", "")
    assert "runtime" in note.lower()
    assert "template" in note.lower() or "Templates" in note


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "crewscore" in result.output.lower()
    from crewscore import __version__

    assert __version__ in result.output
