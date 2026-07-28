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


def test_fix_refuses_coding_agent_config_json(tmp_path: Path):
    """`fix` must not plan governance templates for a build-instructions file.

    It reported overall 0 / STRUCTURAL: CRITICAL GAPS / governance_applicable
    true for an AGENTS.md and planned to inject HIPAA, human-gate and audit
    templates into it.
    """
    config = tmp_path / "AGENTS.md"
    original = "# Build\n\nRun `make test`.\n"
    config.write_text(original, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main, ["fix", "--prompt-file", str(config), "--plan", "--json"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["refused"] is True
    assert payload["profile"] == "coding_agent_config"
    assert payload["governance_applicable"] is False
    assert payload["fixes_planned"] == []
    assert payload["written"] is False
    # No governance grade anywhere in the payload.
    assert "STRUCTURAL" not in json.dumps(payload)
    assert "overall" not in json.dumps(payload)
    assert "--profile system_prompt" in payload["reason"]


def test_fix_refuses_to_modify_a_config_file(tmp_path: Path):
    config = tmp_path / "CLAUDE.md"
    original = "# Guide\n\nUse pnpm. Build with make.\n"
    config.write_text(original, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--prompt-file", str(config), "--apply"])
    assert result.exit_code == 1
    assert config.read_text(encoding="utf-8") == original
    assert "HIPAA" not in config.read_text(encoding="utf-8")
    lower = result.output.lower()
    assert "configuration smells" in lower
    assert "crewscore test" in lower
    assert "--profile system_prompt" in result.output


def test_fix_profile_override_applies_templates_to_config(tmp_path: Path):
    """The refusal has an escape hatch, for parity with test and scan."""
    config = tmp_path / "AGENTS.md"
    config.write_text("# Build\n\nRun make.\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "fix",
            "--prompt-file",
            str(config),
            "--plan",
            "--json",
            "--profile",
            "system_prompt",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["fixes_planned"]


def test_fix_pasted_string_is_still_treated_as_a_prompt():
    """A --prompt string has no path, so it stays governed and fixable."""
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--prompt", "You are helpful.", "--plan", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["fixes_planned"]


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


def test_test_max_smells_gates_system_prompts_too(tmp_path: Path):
    """--max-smells must gate both profiles in `test`, as it already does in `scan`.

    The flag sat inside the not-governance-applicable branch, so a bloated
    system prompt reported smells in JSON and still exited 0 — a silent no-op
    for the CI job that asked to be gated on them.
    """
    prompt_file = tmp_path / "system-prompt.md"
    prompt_file.write_text(
        "You are an agent.\n" + "\n".join(f"- rule {i}" for i in range(250)),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["test", "--prompt-file", str(prompt_file), "--json", "--max-smells", "0"],
    )
    payload = json.loads(result.output)
    assert payload["governance_applicable"] is True
    assert any(s["smell_id"] == "smell.context_bloat" for s in payload["smells"])
    assert result.exit_code == 2


def test_test_max_smells_gates_coding_agent_config(tmp_path: Path):
    """The config half of the same gate — the profile it was written for.

    Without this, the check could be re-nested under `if
    result.governance_applicable:` and CI would stay green.
    """
    config = tmp_path / "AGENTS.md"
    config.write_text(
        "# Guide\n" + "\n".join(f"- rule {i}" for i in range(250)), encoding="utf-8"
    )
    runner = CliRunner()
    failing = runner.invoke(
        main, ["test", "--prompt-file", str(config), "--json", "--max-smells", "0"]
    )
    payload = json.loads(failing.output)
    assert payload["governance_applicable"] is False
    assert any(s["smell_id"] == "smell.context_bloat" for s in payload["smells"])
    assert failing.exit_code == 2

    passing = runner.invoke(
        main, ["test", "--prompt-file", str(config), "--json", "--max-smells", "5"]
    )
    assert passing.exit_code == 0, passing.output


def test_test_max_smells_passes_when_under_limit(tmp_path: Path):
    prompt_file = tmp_path / "system-prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["test", "--prompt-file", str(prompt_file), "--json", "--max-smells", "0"],
    )
    assert result.exit_code == 0, result.output


def test_test_json_warns_when_threshold_ignored_for_config(tmp_path: Path):
    """CI runs with --json, so the ignored-threshold notice must reach the payload."""
    config = tmp_path / "AGENTS.md"
    config.write_text("# Guide\n\nBuild with `make`.\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["test", "--prompt-file", str(config), "--json", "--threshold", "90"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["governance_applicable"] is False
    assert "threshold_ignored_for_config" in payload["warnings"]


def test_test_summary_markdown_reports_the_ignored_threshold(tmp_path: Path):
    """The sticky PR comment / step summary is the consumer that needs this.

    The Action passes --threshold unconditionally (default "50"), so without
    this every config-file comment silently omits that the gate is a no-op.
    """
    config = tmp_path / "AGENTS.md"
    config.write_text("# Guide\n\nBuild with `make`.\n", encoding="utf-8")
    summary = tmp_path / "out.md"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "test",
            "--prompt-file",
            str(config),
            "--json",
            "--threshold",
            "90",
            "--summary",
            str(summary),
        ],
    )
    assert result.exit_code == 0, result.output
    text = summary.read_text(encoding="utf-8")
    assert "threshold_ignored_for_config" in text
    assert "--max-smells" in text


def test_test_json_has_no_threshold_warning_without_threshold(tmp_path: Path):
    config = tmp_path / "AGENTS.md"
    config.write_text("# Guide\n\nBuild with `make`.\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["test", "--prompt-file", str(config), "--json"])
    assert result.exit_code == 0, result.output
    assert "threshold_ignored_for_config" not in json.loads(result.output)["warnings"]


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


def test_fix_plan_human_not_past_tense_applied(tmp_path: Path):
    """Plan mode must not claim fixes were applied (honesty / dry-run)."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(BARE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main, ["fix", "--prompt-file", str(prompt_file), "--plan"]
    )
    assert result.exit_code == 0, result.output
    lower = result.output.lower()
    assert "applied the following" not in lower
    assert "would apply" in lower or "plan" in lower
    assert "runtime" in lower or "gates" in lower or "template" in lower
