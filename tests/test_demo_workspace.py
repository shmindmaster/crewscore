"""The demo workspace is reproducible and carries routine, exception, needs-approval."""

from __future__ import annotations

import hashlib
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main

from scripts import build_demo_workspace as bdw


def _digest(root: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())}


def test_two_builds_are_byte_identical(tmp_path):
    bdw.build(tmp_path / "a")
    bdw.build(tmp_path / "b")
    assert _digest(tmp_path / "a") == _digest(tmp_path / "b")


def test_refuses_non_empty_target_without_force(tmp_path):
    bdw.build(tmp_path / "w")
    assert bdw.main([str(tmp_path / "w")]) == 1
    assert bdw.main([str(tmp_path / "w"), "--force"]) == 0


def test_three_cases_and_the_hero_edit(tmp_path):
    ws = tmp_path / "ws"
    bdw.build(ws)
    run = CliRunner()

    routine = run.invoke(main, ["test", "-f", str(ws / "hardened-ops.md"), "--no-explain", "--threshold", "50"])
    assert routine.exit_code == 0

    ines = ws / "ines-support-assistant.md"
    gate = ["test", "-f", str(ines), "--no-explain", "--require", bdw.CONTROL]
    assert run.invoke(main, gate).exit_code == 2

    before = ines.read_bytes()
    plan = run.invoke(main, ["fix", "--prompt-file", str(ines), "--plan"])
    assert plan.exit_code == 0
    assert ines.read_bytes() == before  # proposes, never writes

    with ines.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(bdw.SENTENCE)
    after = run.invoke(main, gate)
    assert after.exit_code == 0
    assert f"REQUIRED CONTROL COVERED: {bdw.CONTROL}" in after.output
    assert ines.read_bytes() == (ws / "ines-support-assistant.approved.md").read_bytes()


def test_documented_commands_run_verbatim(tmp_path):
    """Every `crewscore test` line in the workspace README is a command that parses."""
    import re
    import shlex

    ws = tmp_path / "ws"
    bdw.build(ws)
    commands = re.findall(r"^\s+(crewscore test .+?)\s+#", (ws / "README.md").read_text("utf-8"), re.M)
    assert len(commands) == 3
    run = CliRunner()
    for command in commands:
        argv = shlex.split(command)[1:]
        argv[argv.index("-f") + 1] = str(ws / argv[argv.index("-f") + 1])
        assert run.invoke(main, argv).exit_code != 1  # 1 would be a usage error


def test_force_refuses_the_current_directory(tmp_path, monkeypatch, capsys):
    bdw.build(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert bdw.main([".", "--force"]) == 1
    assert (tmp_path / "README.md").exists()


def test_non_cp1252_path_does_not_break_output(tmp_path, capsys):
    target = tmp_path / "demo-\U0001f600"
    assert bdw.main([str(target)]) == 0
    out = capsys.readouterr().out
    assert chr(92) + "U0001f600" in out
    out.encode("cp1252")
