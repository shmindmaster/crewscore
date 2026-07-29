"""Eval handoff artifacts for Promptfoo / garak (never executed by CrewScore)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.export_eval import (
    analyze_for_export,
    garak_probes_for_gaps,
    promptfoo_cases_for_gaps,
    write_eval_stubs,
)
from crewscore.scoring import RULESET_ID
from crewscore.scorers.structural_analysis import CONCEPTS


def test_write_eval_stubs_includes_manifest_and_ruleset(tmp_path: Path):
    paths = write_eval_stubs(tmp_path / "out", system_prompt="You are helpful.")
    assert len(paths) == 3
    names = {p.name for p in paths}
    assert names == {
        "promptfooconfig.yaml",
        "README-EVAL.md",
        "crewscore-eval-manifest.json",
    }

    yaml_text = (tmp_path / "out" / "promptfooconfig.yaml").read_text(encoding="utf-8")
    assert "You are helpful" in yaml_text
    assert RULESET_ID in yaml_text
    assert "promptfoo" in yaml_text.lower()
    assert "Injection:" in yaml_text or "injection" in yaml_text.lower()

    readme = (tmp_path / "out" / "README-EVAL.md").read_text(encoding="utf-8")
    assert "garak" in readme.lower()
    assert RULESET_ID in readme
    assert "not" in readme.lower() and "safe in production" in readme.lower()

    manifest = json.loads(
        (tmp_path / "out" / "crewscore-eval-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["ruleset"] == RULESET_ID
    assert manifest["honesty"]["runs_live_evals"] is False
    assert "prompt" not in manifest  # prompt text must not be in the manifest
    assert manifest["structural"]["missing_control_count"] == 23
    assert manifest["promptfoo"]["case_count"] >= 1
    assert manifest["garak"]["suggested_probes"]


def test_cases_bias_toward_missing_dimensions():
    bare = analyze_for_export("You are a helpful assistant.")
    assert bare["missing_control_count"] == 23
    cases = promptfoo_cases_for_gaps(bare["missing_dimensions"])
    descriptions = " ".join(c["description"] for c in cases).lower()
    assert "injection" in descriptions
    assert "human gate" in descriptions or "human" in descriptions

    # Fully covered fixture should still emit a minimal scaffold.
    all_controls = []
    for concepts in CONCEPTS.values():
        for c in concepts:
            all_controls.append(c.label)
    # Use analyze gaps of empty missing list path
    cases_full = promptfoo_cases_for_gaps([])
    assert len(cases_full) >= 1
    assert any("injection" in c["description"].lower() for c in cases_full)


def test_garak_probes_for_injection_gap():
    probes = garak_probes_for_gaps(["injection", "hallucination"])
    assert "promptinject" in probes
    assert len(probes) >= 2


def test_cli_export_eval(tmp_path: Path):
    runner = CliRunner()
    out = tmp_path / "eval"
    result = runner.invoke(
        main,
        [
            "export-eval",
            "--prompt",
            "You are a support agent.",
            "--output-dir",
            str(out),
            "--provider",
            "openai:gpt-4o",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "promptfooconfig.yaml").is_file()
    assert (out / "README-EVAL.md").is_file()
    assert (out / "crewscore-eval-manifest.json").is_file()
    assert "promptfoo" in result.output.lower()
    yaml_text = (out / "promptfooconfig.yaml").read_text(encoding="utf-8")
    assert "openai:gpt-4o" in yaml_text
