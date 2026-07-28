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


def test_scan_summary_writes_markdown(tmp_path: Path):
    """scan --summary writes transparent multi-file markdown."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "a.md").write_text(BARE, encoding="utf-8")
    summary = tmp_path / "out.md"
    runner = CliRunner()
    result = runner.invoke(
        main, ["scan", str(tmp_path), "--summary", str(summary)]
    )
    assert result.exit_code == 0, result.output
    text = summary.read_text(encoding="utf-8")
    assert "CrewScore" in text
    assert "0/100" in text or "Path" in text
    assert "crewscore-hygiene@" in text


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


def test_fix_plan_json_lists_dimensions_without_writing(tmp_path: Path):
    """--plan --json lists planned dimensions and never mutates the file."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["fix", "--prompt-file", str(prompt_file), "--plan", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "fixes_planned" in payload
    assert isinstance(payload["fixes_planned"], list)
    assert len(payload["fixes_planned"]) > 0
    assert prompt_file.read_text(encoding="utf-8") == BARE
    assert payload.get("written") is not True


def test_fix_plan_does_not_write_with_apply_ignored_or_explicit(tmp_path: Path):
    """--plan is mutually exclusive with --apply and --output."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    out_file = tmp_path / "out.md"
    runner = CliRunner()

    with_apply = runner.invoke(
        main,
        [
            "fix",
            "--prompt-file",
            str(prompt_file),
            "--plan",
            "--apply",
        ],
    )
    assert with_apply.exit_code == 1
    assert "plan" in with_apply.output.lower() or "mutually" in with_apply.output.lower()
    assert prompt_file.read_text(encoding="utf-8") == BARE

    with_output = runner.invoke(
        main,
        [
            "fix",
            "--prompt-file",
            str(prompt_file),
            "--plan",
            "--output",
            str(out_file),
        ],
    )
    assert with_output.exit_code == 1
    assert "plan" in with_output.output.lower() or "mutually" in with_output.output.lower()
    assert prompt_file.read_text(encoding="utf-8") == BARE
    assert not out_file.exists()


def test_fix_plan_human_mentions_plan(tmp_path: Path):
    """Human --plan output uses plan language and names at least one dimension."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["fix", "--prompt-file", str(prompt_file), "--plan"],
    )
    assert result.exit_code == 0, result.output
    lower = result.output.lower()
    assert "plan" in lower or "would apply" in lower
    # At least one known fix dimension name appears in human output
    dimension_names = [
        "injection",
        "hallucination",
        "citation",
        "cost",
        "human_gate",
        "safe_stop",
        "audit",
        "compliance",
    ]
    assert any(name in lower for name in dimension_names)
    assert prompt_file.read_text(encoding="utf-8") == BARE
