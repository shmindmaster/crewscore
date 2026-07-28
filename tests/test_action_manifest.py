"""Manifest checks for the official CrewScore GitHub Action."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def _action_text() -> str:
    return Path("action.yml").read_text(encoding="utf-8")


def _outputs_script() -> str:
    """The inline Python from the `Run CrewScore` step that sets score/tier.

    GitHub strips the YAML block-scalar indentation before running the step,
    so the snippet reaches python at column 0 — dedent to match.
    """
    body = _action_text().split('echo "$OUTPUT" | python -c "', 1)[1]
    return textwrap.dedent(body.split('\n        "', 1)[0])


def _run_outputs(payload, tmp_path) -> dict[str, str]:
    """Execute the step's output script over a CrewScore JSON payload."""
    gh_output = tmp_path / "github_output.txt"
    gh_output.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-c", _outputs_script()],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, "GITHUB_OUTPUT": str(gh_output)},
    )
    assert proc.returncode == 0, proc.stderr
    return dict(
        line.split("=", 1)
        for line in gh_output.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def test_action_yml_present():
    text = _action_text()
    assert "prompt-file" in text
    assert "threshold" in text
    assert "crewscore" in text.lower()


def test_action_scan_path_input_optional_and_prompt_file_not_required():
    """scan-path is optional; prompt-file is not required (XOR validated in script)."""
    text = _action_text()
    assert "scan-path:" in text
    # prompt-file must not be hard-required so scan-path-only consumers work
    assert "prompt-file:" in text
    # After prompt-file block, required should be false (composite XOR)
    prompt_block = text.split("prompt-file:")[1].split("threshold:")[0]
    assert "required: false" in prompt_block
    scan_block = text.split("scan-path:")[1].split("\n  ")[0:6]
    scan_joined = "\n".join(scan_block) if isinstance(scan_block, list) else scan_block
    # Full text still needs required:false near scan-path
    assert "scan-path" in text and "required: false" in text


def test_action_script_runs_scan_when_scan_path_set():
    """Non-empty scan-path runs crewscore scan and picks worst (min) overall."""
    text = _action_text()
    assert 'ARGS=(scan' in text or "ARGS=(scan" in text
    assert "--json" in text
    assert "--threshold" in text
    # Worst score from multi-file scan JSON (list of {overall, tier})
    assert "overall" in text
    assert "min(" in text
    assert "isinstance(data, list)" in text


def test_action_scan_and_test_both_pass_summary():
    """Both scan and single-file paths must write --summary when configured."""
    text = _action_text()
    assert "summary:" in text
    assert "--summary" in text
    assert "pr-comment:" in text
    assert "crewscore-sticky" in text
    assert "summary-path" in text


def test_action_outputs_ignore_coding_agent_config(tmp_path: Path):
    """A repo's AGENTS.md must not set score=0 for a hardened system prompt."""
    outputs = _run_outputs(
        [
            {
                "path": "AGENTS.md",
                "overall": 0,
                "tier": "CONFIG: NO SMELLS DETECTED",
                "governance_applicable": False,
            },
            {
                "path": "prompts/system-prompt.md",
                "overall": 87,
                "tier": "STRUCTURAL: OK WITH GAPS",
                "governance_applicable": True,
            },
        ],
        tmp_path,
    )
    assert outputs["score"] == "87"
    assert outputs["tier"] == "STRUCTURAL: OK WITH GAPS"


def test_action_outputs_still_report_worst_governed_file(tmp_path: Path):
    outputs = _run_outputs(
        [
            {"path": "a.md", "overall": 87, "tier": "STRUCTURAL: OK WITH GAPS",
             "governance_applicable": True},
            {"path": "b.md", "overall": 41, "tier": "STRUCTURAL: CRITICAL GAPS",
             "governance_applicable": True},
        ],
        tmp_path,
    )
    assert outputs["score"] == "41"
    assert outputs["tier"] == "STRUCTURAL: CRITICAL GAPS"


def test_action_outputs_empty_when_no_governed_files(tmp_path: Path):
    """No system prompt scanned means no score — 0 would be a lie, not a grade."""
    outputs = _run_outputs(
        [
            {"path": "AGENTS.md", "overall": 0, "tier": "CONFIG: 1 SMELL",
             "governance_applicable": False},
            {"path": "CLAUDE.md", "overall": 0, "tier": "CONFIG: NO SMELLS DETECTED",
             "governance_applicable": False},
        ],
        tmp_path,
    )
    assert outputs["score"] == ""
    assert outputs["tier"] == ""


def test_action_outputs_single_file_config_payload_is_empty(tmp_path: Path):
    """`test --prompt-file AGENTS.md` emits one dict, not a list."""
    outputs = _run_outputs(
        {
            "overall": 0,
            "tier": "CONFIG: NO SMELLS DETECTED",
            "governance_applicable": False,
        },
        tmp_path,
    )
    assert outputs["score"] == ""
    assert outputs["tier"] == ""


def test_action_outputs_single_file_prompt_payload(tmp_path: Path):
    outputs = _run_outputs(
        {"overall": 62, "tier": "STRUCTURAL: WEAK", "governance_applicable": True},
        tmp_path,
    )
    assert outputs["score"] == "62"
    assert outputs["tier"] == "STRUCTURAL: WEAK"


def test_action_outputs_default_missing_governance_key_to_governed(tmp_path: Path):
    """Older payloads predate profiles; they were all judged on the score."""
    outputs = _run_outputs(
        [
            {"path": "a.md", "overall": 30, "tier": "STRUCTURAL: CRITICAL GAPS"},
            {"path": "b.md", "overall": 70, "tier": "STRUCTURAL: OK WITH GAPS"},
        ],
        tmp_path,
    )
    assert outputs["score"] == "30"


def test_action_outputs_document_the_empty_case():
    """The empty-string contract is documented where consumers read it."""
    text = _action_text()
    outputs_block = text.split("outputs:", 1)[1].split("runs:", 1)[0]
    score_desc = outputs_block.split("score:", 1)[1].split("value:", 1)[0]
    assert "empty" in score_desc.lower()
    tier_desc = outputs_block.split("tier:", 1)[1].split("value:", 1)[0]
    assert "empty" in tier_desc.lower()


def test_action_script_requires_prompt_file_or_scan_path():
    """Script must fail if neither prompt-file nor scan-path is provided."""
    text = _action_text()
    assert "scan-path" in text
    # Human-readable validation in the composite run step
    lower = text.lower()
    assert (
        "either" in lower
        or "one of" in lower
        or "required" in lower and "prompt-file" in lower and "scan-path" in lower
    )
    assert "exit 1" in text or 'exit 1' in text
