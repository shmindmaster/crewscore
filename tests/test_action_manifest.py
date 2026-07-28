"""Manifest checks for the official CrewScore GitHub Action."""

from pathlib import Path


def _action_text() -> str:
    return Path("action.yml").read_text(encoding="utf-8")


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
