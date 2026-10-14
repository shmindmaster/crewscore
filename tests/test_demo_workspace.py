"""The demo workspace is reproducible and carries routine, exception, needs-approval."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_demo_workspace as bdw  # noqa: E402


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
