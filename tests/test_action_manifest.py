"""Manifest checks for the official CrewScore GitHub Action."""

import json
import os
import re
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


def _run_crewscore_step_block() -> tuple[str, str]:
    """The `Run CrewScore` step split into (head, script).

    `head` is everything before `run: |` (the `shell:`/`env:` lines);
    `script` is the dedented `run: |` block body — the surrounding bash
    kept intact (the `echo "$OUTPUT" | python -c "..."` pipe, the
    double-quoted heredoc that embeds the python snippet), so it can be
    executed through a real bash interpreter instead of handed to python
    directly.
    """
    body = _action_text().split("- name: Run CrewScore", 1)[1]
    body = body.split("- name: Sticky PR comment", 1)[0]
    head, script = body.split("run: |\n", 1)
    return head, textwrap.dedent(script)


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

    # GitHub Actions resolves `${{ inputs.X }}` before bash ever sees the
    # step: values declared under `env:` become literal OS env vars, and any
    # left directly in the `run:` body are text-substituted into the script.
    # `_resolve_run_crewscore_step` reproduces both paths from the current
    # action.yml, whichever it uses.
    inputs = {
        "prompt-file": prompt_file,
        "scan-path": "",
        "threshold": "50",
        "max-smells": "",
        "explain": "false",
        "summary": "",
    }
    script, extra_env = _resolve_run_crewscore_step(inputs)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "crewscore"
    # Write with explicit LF — bash's shebang line rejects a CRLF-terminated
    # interpreter path, and Path.write_text translates \n to \r\n on Windows.
    shell_stdout = stub_stdout.replace("'", "'\"'\"'")
    with open(stub, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/bash\n")
        # printf is a POSIX shell builtin.  Using it instead of `cat` keeps
        # this hermetic even when Git Bash receives a Windows-style PATH.
        f.write(f"printf '%s\\n' '{shell_stdout}'\n")
        f.write(f"exit {stub_exit}\n")
    stub.chmod(0o755)

    gh_output = tmp_path / "github_output.txt"
    gh_output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        **extra_env,
    }
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


def _resolve_run_crewscore_step(inputs: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Reproduce how the GitHub Actions runner materializes this step for bash.

    Two mechanisms exist for `${{ inputs.x }}` to reach the step:
    - Declared under the step's `env:` block: the runner assigns the
      resolved value as a literal OS environment variable. Bash never
      re-parses that text, so shell metacharacters in it are inert.
    - Left directly in the `run:` script body: GitHub does a textual
      substitution into the YAML *before* bash ever sees the script, so
      shell metacharacters in the value become part of the parsed script
      (the script-injection exposure).

    Returns (script, env_vars) so callers can exercise either path exactly
    as the real runner would, whichever the current action.yml uses.
    """
    head, script = _run_crewscore_step_block()

    env_vars: dict[str, str] = {}
    if "env:" in head:
        env_section = head.split("env:", 1)[1]
        for line in env_section.splitlines():
            stripped = line.strip()
            match = re.fullmatch(
                r"(\w+):\s*\$\{\{\s*inputs\.([\w-]+)\s*\}\}", stripped
            )
            if match:
                var_name, input_key = match.groups()
                env_vars[var_name] = inputs.get(input_key, "")

    for input_key, value in inputs.items():
        script = script.replace("${{ inputs." + input_key + " }}", value)
    return script, env_vars


def test_action_step_never_splices_a_malicious_input_into_the_shell(tmp_path: Path):
    """A malicious input value must reach the CLI as literal text, never execute.

    `${{ inputs.* }}` spliced directly into the `run:` script body is the
    documented GitHub Actions script-injection pattern: a consumer who wires
    an input to attacker-controlled data (a PR title, a branch name) gets
    that text executed as shell. The mitigation is passing inputs through
    the step's `env:` block instead, where they arrive as literal
    environment variable values bash never re-parses.
    """
    bash = _resolve_bash()
    if bash is None:
        pytest.skip("no real bash interpreter found for the end-to-end step test")

    marker = tmp_path / "INJECTED"
    payload = f'x"; touch "{marker.as_posix()}"; echo "'
    inputs = {
        "prompt-file": payload,
        "scan-path": "",
        "threshold": "50",
        "max-smells": "",
        "explain": "false",
        "summary": "",
    }
    script, extra_env = _resolve_run_crewscore_step(inputs)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "crewscore"
    argv_file = tmp_path / "argv.txt"
    with open(stub, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/bash\n")
        f.write(f'printf "%s\\n" "$@" > "{argv_file.as_posix()}"\n')
        f.write("cat <<'STUBEOF'\n")
        f.write(
            json.dumps(
                {"overall": 10, "tier": "STRUCTURAL: WEAK", "governance_applicable": True}
            )
        )
        f.write("\nSTUBEOF\n")
        f.write("exit 0\n")
    stub.chmod(0o755)

    gh_output = tmp_path / "github_output.txt"
    gh_output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        **extra_env,
    }
    env["GITHUB_OUTPUT"] = str(gh_output)

    subprocess.run(
        [bash, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )

    assert not marker.exists(), (
        "malicious input value executed as shell code instead of being "
        "passed through as literal text — inputs must be wired via env:, "
        "not spliced into the run: script body"
    )
    argv = argv_file.read_text(encoding="utf-8").splitlines() if argv_file.exists() else []
    assert payload in argv, "the literal (unexecuted) payload should still reach the CLI"


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


def test_action_description_does_not_overclaim_production_readiness():
    """Marketplace listing text must match what the tool actually does.

    docs/validation.md is the source of truth: the score does not establish
    production readiness. The top-level description must not claim
    production-readiness assessment or certification.
    """
    text = _action_text()
    description_line = next(
        line for line in text.splitlines() if line.startswith("description:")
    )
    lowered = description_line.lower()
    assert "production-readiness" not in lowered
    assert "production readiness" not in lowered
    assert "certif" not in lowered


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


def test_action_defaults_to_report_only_and_exposes_control_policy_inputs():
    """The Action must not silently treat coverage as a safety threshold.

    Existing consumers can still opt into the legacy threshold, but a new
    workflow starts report-only and chooses either exact controls or a
    prompt-free regression baseline before it can fail.
    """
    manifest = _action_manifest()
    assert manifest["inputs"]["threshold"]["default"] == ""
    for name in (
        "required-controls",
        "forbid-missing",
        "baseline",
        "fail-on-regression",
        "config",
        "sarif",
    ):
        assert name in manifest["inputs"]
    text = _action_text()
    assert 'ARGS=(scan "$SCAN_PATH" --json)' in text
    assert 'ARGS=(test --prompt-file "$PROMPT_FILE" --json)' in text
    assert 'ARGS+=(--require "$REQUIRED_CONTROLS")' in text
    assert 'ARGS+=(--fail-on-regression)' in text
    assert 'ARGS+=(--sarif "$SARIF")' in text


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
    # The worked example moved to docs/ci.md with the rest of the CI content.
    # The README keeps only the warning, because a reader who never opens the
    # linked doc still has to learn that an empty score casts to 0.
    docs = Path("docs/ci.md").read_text(encoding="utf-8")
    assert "outputs.scored == 'true'" in docs
    assert "outputs.score != ''" not in docs
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "scored" in readme, "README drops the empty-score guard entirely"

# ─── GitHub Marketplace listing requirements ──────────────────────────
#
# The Marketplace publish form validates action.yml and refuses the listing if
# any of these is wrong. Discovering that in a browser, after the release is
# already tagged and published, costs an extra release to fix - which is
# exactly what the 211-character description on v0.5.0 cost.

MARKETPLACE_DESCRIPTION_LIMIT = 125


def _action_manifest() -> dict:
    import yaml

    return yaml.safe_load(_action_text())


def test_action_description_fits_the_marketplace_limit():
    """GitHub rejects the listing over 125 characters and the form offers no
    override - the fix has to ship in a new tagged release."""
    desc = _action_manifest()["description"]
    assert len(desc) < MARKETPLACE_DESCRIPTION_LIMIT, (
        f"{len(desc)} chars; Marketplace requires < "
        f"{MARKETPLACE_DESCRIPTION_LIMIT}"
    )


def test_action_declares_every_field_the_marketplace_requires():
    m = _action_manifest()
    assert m.get("name"), "Marketplace requires a name"
    assert m.get("description"), "Marketplace requires a description"
    branding = m.get("branding") or {}
    assert branding.get("icon"), "Marketplace requires branding.icon"
    assert branding.get("color"), "Marketplace requires branding.color"
    # The colour list is closed; anything outside it is refused at publish.
    assert branding["color"] in {
        "white", "yellow", "blue", "green",
        "orange", "red", "purple", "gray-dark",
    }, branding["color"]


def test_action_description_parses_as_a_string_not_a_broken_mapping():
    """An unquoted colon in a YAML scalar turns the line into a mapping and
    breaks the whole manifest. Hit once while shortening the description for
    the Marketplace limit; this reparse is the guard."""
    m = _action_manifest()
    assert isinstance(m["description"], str), (
        f"description parsed as {type(m['description']).__name__} - "
        "an unquoted colon has broken the manifest"
    )

