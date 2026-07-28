"""Manifest checks for the official CrewScore GitHub Action."""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


def _action_text() -> str:
    return Path("action.yml").read_text(encoding="utf-8")


def _resolve_bash() -> str | None:
    """Find a real bash binary for the end-to-end step tests.

    On Windows, a bare `bash` on PATH can resolve to the legacy WSL launcher
    shim (`C:\\Windows\\System32\\bash.exe`), which runs the script inside a
    separate WSL filesystem/PATH namespace (Windows paths need `/mnt/c/...`
    translation) and was inconsistent across invocations in development.
    Git for Windows' MSYS2 bash is deterministic and installed alongside any
    `git` install, so prefer it explicitly. On non-Windows, plain `bash` on
    PATH is the real CI shell (the action itself runs on ubuntu-latest).
    """
    if os.name != "nt":
        return shutil.which("bash")
    for candidate in (
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def _outputs_script() -> str:
    """The inline Python from the `Run CrewScore` step that sets score/tier.

    GitHub strips the YAML block-scalar indentation before running the step,
    so the snippet reaches python at column 0 — dedent to match.
    """
    body = _action_text().split('echo "$OUTPUT" | python -c "', 1)[1]
    return textwrap.dedent(body.split('\n        "', 1)[0])


def _run_crewscore_step_script() -> str:
    """The full `run: |` block of the `Run CrewScore` step, dedented.

    Unlike `_outputs_script`, this keeps the surrounding bash — the
    `echo "$OUTPUT" | python -c "..."` pipe, the double-quoted heredoc that
    embeds the python snippet, and the `${{ inputs.* }}` variable
    assignments — so it can be executed through a real bash interpreter
    instead of handed to python directly.
    """
    body = _action_text().split("- name: Run CrewScore", 1)[1]
    body = body.split("- name: Sticky PR comment", 1)[0]
    script = body.split("run: |\n", 1)[1]
    return textwrap.dedent(script)


def _run_crewscore_step_via_bash(
    tmp_path,
    stub_stdout: str,
    stub_exit: int = 0,
    prompt_file: str = "prompt.md",
) -> tuple[int, str, dict[str, str]]:
    """Run the real step script through a real bash, exercising the actual
    quoting/piping layer end to end (not just the embedded python snippet).

    A fake `crewscore` executable stands in for the real CLI so this stays
    hermetic; everything downstream of its stdout — the bash double-quoting,
    the pipe into `python -c "..."`, and the GITHUB_OUTPUT writes — is real.
    """
    bash = _resolve_bash()
    if bash is None:
        pytest.skip("no real bash interpreter found for the end-to-end step test")

    script = _run_crewscore_step_script()
    # GitHub Actions substitutes `${{ inputs.X }}` with literal text before
    # bash ever sees the script; reproduce that substitution here.
    substitutions = {
        "${{ inputs.prompt-file }}": prompt_file,
        "${{ inputs.scan-path }}": "",
        "${{ inputs.threshold }}": "50",
        "${{ inputs.max-smells }}": "",
        "${{ inputs.explain }}": "false",
        "${{ inputs.summary }}": "",
    }
    for token, value in substitutions.items():
        script = script.replace(token, value)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "crewscore"
    # Write with explicit LF — bash's shebang line rejects a CRLF-terminated
    # interpreter path, and Path.write_text translates \n to \r\n on Windows.
    with open(stub, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/bash\n")
        f.write(f"cat <<'STUBEOF'\n{stub_stdout}\nSTUBEOF\n")
        f.write(f"exit {stub_exit}\n")
    stub.chmod(0o755)

    gh_output = tmp_path / "github_output.txt"
    gh_output.write_text("", encoding="utf-8")
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env["GITHUB_OUTPUT"] = str(gh_output)

    proc = subprocess.run(
        [bash, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    outputs = dict(
        line.split("=", 1)
        for line in gh_output.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    return proc.returncode, proc.stderr, outputs


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


def test_action_declares_scored_output_wired_to_the_step():
    """`scored` is a real declared output, not just something the step writes.

    A step that writes `scored=` to GITHUB_OUTPUT is invisible to consumers
    unless the composite action re-exports it under `outputs:`.
    """
    outputs_block = _action_text().split("outputs:", 1)[1].split("runs:", 1)[0]
    assert "scored:" in outputs_block
    scored_value = outputs_block.split("scored:", 1)[1].split("value:", 1)[1]
    assert "steps.run.outputs.scored" in scored_value


def test_action_scored_output_description_states_its_crash_failure_mode():
    """`scored` must document that a CLI crash leaves it as the empty string.

    If `crewscore` emits non-JSON (a crash), `set -euo pipefail` kills the
    step before any of scored/score/tier is written, so `scored` reads ''
    — neither 'true' nor 'false'. `scored == 'true'` fails safe; a bare
    `if: outputs.scored` or `scored == 'false'` would misread it, since
    GitHub treats the non-empty string 'false' as truthy. The description
    must say so, not just define the true/false cases.
    """
    outputs_block = _action_text().split("outputs:", 1)[1].split("runs:", 1)[0]
    scored_desc = outputs_block.split("scored:", 1)[1].split("value:", 1)[0]
    lower = scored_desc.lower()
    assert "empty string" in lower or "''" in scored_desc
    assert "crash" in lower or "non-json" in lower
    assert "scored == 'true'" in scored_desc


def test_action_scored_output_is_true_when_a_prompt_was_scored(tmp_path: Path):
    outputs = _run_outputs(
        [
            {"path": "AGENTS.md", "overall": 0, "tier": "CONFIG: 1 SMELL",
             "governance_applicable": False},
            {"path": "p.md", "overall": 87, "tier": "STRUCTURAL: OK WITH GAPS",
             "governance_applicable": True},
        ],
        tmp_path,
    )
    assert outputs["scored"] == "true"


def test_action_scored_output_is_false_when_nothing_was_graded(tmp_path: Path):
    """GitHub casts '' to 0 in numeric comparisons, so `score` cannot guard itself.

    `if: outputs.score < 50` evaluates 0 < 50 -> true on a config-only repo and
    fires a "score too low" branch for a run that measured nothing. `scored` is
    the flag a consumer can actually guard on.
    """
    outputs = _run_outputs(
        [
            {"path": "AGENTS.md", "overall": 0, "tier": "CONFIG: 1 SMELL",
             "governance_applicable": False},
        ],
        tmp_path,
    )
    assert outputs["scored"] == "false"
    assert outputs["score"] == ""
    assert outputs["tier"] == ""


def test_action_scored_output_is_false_for_single_config_file(tmp_path: Path):
    outputs = _run_outputs(
        {"overall": 0, "tier": "CONFIG: NO SMELLS DETECTED",
         "governance_applicable": False},
        tmp_path,
    )
    assert outputs["scored"] == "false"


def test_action_output_script_triggers_no_shell_substitution():
    """The step passes this snippet inside a bash double-quoted string.

    A backtick or $( ) anywhere in it — including in a Python comment — is
    command substitution: bash executes the text and splices its output into
    the code. Prose punctuation must not become a shell command. A bare `$`
    (e.g. `$foo`) is lower risk under `set -u` (it aborts loudly rather than
    expanding silently) but should not appear either.
    """
    snippet = _action_text().split('echo "$OUTPUT" | python -c "', 1)[1].split(
        '\n        "', 1
    )[0]
    assert "`" not in snippet
    assert "$(" not in snippet
    assert "$" not in snippet


def test_action_outputs_document_the_scored_guard():
    """score/tier descriptions must name the guard, not imply '' protects itself."""
    outputs_block = _action_text().split("outputs:", 1)[1].split("runs:", 1)[0]
    guard = "scored == 'true'"
    score_desc = outputs_block.split("score:", 1)[1].split("value:", 1)[0]
    assert guard in score_desc
    tier_desc = outputs_block.split("tier:", 1)[1].split("value:", 1)[0]
    assert guard in tier_desc


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


def test_action_step_runs_end_to_end_through_real_bash(tmp_path: Path):
    """The step script — bash quoting, the pipe, and the embedded python —
    all run through a real bash interpreter, not just the python snippet in
    isolation. This is the one test that exercises the actual quoting layer
    `_run_outputs` bypasses by invoking the snippet via `sys.executable`.
    """
    returncode, stderr, outputs = _run_crewscore_step_via_bash(
        tmp_path,
        stub_stdout=json.dumps(
            {"overall": 62, "tier": "STRUCTURAL: WEAK", "governance_applicable": True}
        ),
    )
    assert returncode == 0, stderr
    assert outputs["scored"] == "true"
    assert outputs["score"] == "62"
    assert outputs["tier"] == "STRUCTURAL: WEAK"


def test_action_step_end_to_end_config_only_yields_empty_score(tmp_path: Path):
    """Real bash run: a config-only payload must not leak a numeric score."""
    _, _, outputs = _run_crewscore_step_via_bash(
        tmp_path,
        stub_stdout=json.dumps(
            {"overall": 0, "tier": "CONFIG: NO SMELLS DETECTED",
             "governance_applicable": False}
        ),
    )
    assert outputs["scored"] == "false"
    assert outputs["score"] == ""
    assert outputs["tier"] == ""


def test_action_step_end_to_end_propagates_crewscore_exit_code(tmp_path: Path):
    """Real bash run: the step must exit with the underlying CLI's code."""
    returncode, _, _ = _run_crewscore_step_via_bash(
        tmp_path,
        stub_stdout=json.dumps(
            {"overall": 30, "tier": "STRUCTURAL: CRITICAL GAPS",
             "governance_applicable": True}
        ),
        stub_exit=2,
    )
    assert returncode == 2


def test_readme_output_guard_example_uses_scored():
    """The documented Action guard should use `scored`, not a `score != ''` check.

    `score != '' && score < 50` is correct under GitHub's short-circuit `&&`
    semantics, but it predates the `scored` output and is not the guard a
    consumer should copy — `scored == 'true'` is simpler and explicit.
    """
    text = Path("README.md").read_text(encoding="utf-8")
    assert "outputs.scored == 'true'" in text
    assert "outputs.score != ''" not in text
