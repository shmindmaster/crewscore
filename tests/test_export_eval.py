"""Eval handoff stubs for Promptfoo / garak."""

from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.export_eval import write_eval_stubs


def test_write_eval_stubs(tmp_path: Path):
    paths = write_eval_stubs(tmp_path / "out", system_prompt="You are helpful.")
    assert len(paths) == 2
    yaml_text = (tmp_path / "out" / "promptfooconfig.yaml").read_text(encoding="utf-8")
    assert "You are helpful" in yaml_text
    assert "promptfoo" in yaml_text.lower()
    readme = (tmp_path / "out" / "README-EVAL.md").read_text(encoding="utf-8")
    assert "garak" in readme.lower()
    assert "CrewScore" in readme


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
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "promptfooconfig.yaml").is_file()
    assert (out / "README-EVAL.md").is_file()
    assert "promptfoo" in result.output.lower()
