"""Contract tests for explicit control policies, baselines, SARIF, and init."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.policy import BASELINE_FORMAT


BARE = "You are a helpful assistant."
HUMAN_GATE = """
Human-in-the-loop review is required before execute, send, or publish actions.
Do not automatically execute actions without human review and approval.
"""


def _prompt(root: Path, text: str = BARE) -> Path:
    path = root / "prompts" / "system-prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_explicit_control_policy_fails_without_changing_score_payload():
    runner = CliRunner()
    ordinary = runner.invoke(main, ["test", "--prompt", BARE, "--json"])
    gated = runner.invoke(
        main,
        [
            "test",
            "--prompt",
            BARE,
            "--json",
            "--require",
            "human_gate.approval_required",
        ],
    )
    assert ordinary.exit_code == 0, ordinary.output
    assert gated.exit_code == 2, gated.output
    before = json.loads(ordinary.stdout)
    after = json.loads(gated.stdout)
    # The reason for exit 2 must be visible even in --json mode (stderr).
    assert "Required-control failure" in gated.stderr
    assert after["overall"] == before["overall"]
    assert after["dimensions"] == before["dimensions"]
    assert after["tier"] == before["tier"]
    assert after["policy"]["missing_required_controls"] == [
        "human_gate.approval_required"
    ]


def test_dimension_selector_requires_each_published_control():
    runner = CliRunner()
    passing = runner.invoke(
        main, ["test", "--prompt", HUMAN_GATE, "--json", "--require", "human_gate"]
    )
    assert passing.exit_code == 0, passing.output
    policy = json.loads(passing.output)["policy"]
    assert policy["missing_required_controls"] == []
    assert set(policy["required_controls"]) == {
        "human_gate.approval_required",
        "human_gate.no_autonomous_action",
    }


def test_baseline_fails_only_after_a_found_control_regresses(tmp_path: Path):
    prompt = _prompt(tmp_path, HUMAN_GATE)
    baseline = tmp_path / ".crewscore-baseline.json"
    runner = CliRunner()
    create = runner.invoke(
        main, ["baseline", str(tmp_path), "--output", str(baseline)]
    )
    assert create.exit_code == 0, create.output
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    assert payload["format"] == BASELINE_FORMAT
    assert "Human-in-the-loop" not in baseline.read_text(encoding="utf-8")

    unchanged = runner.invoke(
        main,
        [
            "scan",
            str(tmp_path),
            "--json",
            "--baseline",
            str(baseline),
            "--fail-on-regression",
        ],
    )
    assert unchanged.exit_code == 0, unchanged.output

    prompt.write_text(BARE, encoding="utf-8")
    regressed = runner.invoke(
        main,
        [
            "scan",
            str(tmp_path),
            "--json",
            "--baseline",
            str(baseline),
            "--fail-on-regression",
        ],
    )
    assert regressed.exit_code == 2, regressed.output
    row = json.loads(regressed.stdout)[0]
    assert "human_gate.approval_required" in row["policy"]["regressed_controls"]


def test_sarif_is_prompt_free_and_reports_missing_controls(tmp_path: Path):
    sentinel = "DO-NOT-LEAK-THE-PROMPT-7f5a"
    prompt = _prompt(tmp_path, f"{BARE}\n{sentinel}")
    sarif = tmp_path / "crewscore.sarif"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["test", "--prompt-file", str(prompt), "--json", "--sarif", str(sarif)],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(sarif.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert sentinel not in serialized
    assert report["version"] == "2.1.0"
    results = report["runs"][0]["results"]
    assert any(row["ruleId"] == "crewscore.human_gate.approval_required" for row in results)
    assert all("snippet" not in row for row in results)


def test_policy_never_turns_coding_agent_config_into_a_governance_grade(tmp_path: Path):
    config = tmp_path / "AGENTS.md"
    config.write_text("# Build\n\nRun tests.\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "test",
            "--prompt-file",
            str(config),
            "--json",
            "--require",
            "human_gate.approval_required",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "overall" not in payload
    assert "findings" not in payload
    assert payload["policy"]["applicable"] is False
    assert payload["policy"]["failed"] is False


def test_small_project_config_enforces_controls_without_a_yaml_runtime_dependency(
    tmp_path: Path,
):
    _prompt(tmp_path, HUMAN_GATE)
    policy = tmp_path / ".crewscore.yml"
    policy.write_text(
        "version: 1\nrequired_controls:\n  - human_gate.approval_required\nforbid_missing: []\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    passing = runner.invoke(main, ["scan", str(tmp_path), "--json", "--config", str(policy)])
    assert passing.exit_code == 0, passing.output
    _prompt(tmp_path).write_text(BARE, encoding="utf-8")
    failing = runner.invoke(main, ["scan", str(tmp_path), "--json", "--config", str(policy)])
    assert failing.exit_code == 2, failing.output
    assert json.loads(failing.stdout)[0]["policy"]["failed"] is True


def test_init_creates_non_deploying_regression_setup(tmp_path: Path):
    _prompt(tmp_path, HUMAN_GATE)
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    config = (tmp_path / ".crewscore.yml").read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "crewscore.yml").read_text(
        encoding="utf-8"
    )
    baseline = json.loads((tmp_path / ".crewscore-baseline.json").read_text(encoding="utf-8"))
    assert "fail_on_regression: true" in config
    assert "required_controls: []" in config
    assert "config: .crewscore.yml" in workflow
    assert "sarif: crewscore.sarif" in workflow
    # pr-comment defaults on; without this permission every same-repo PR
    # comment 403s and the first-run experience is a red check.
    assert "pull-requests: write" in workflow
    assert "deploy" not in workflow.lower()
    assert baseline["format"] == BASELINE_FORMAT
