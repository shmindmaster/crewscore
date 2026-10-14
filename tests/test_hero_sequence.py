"""The demo hero: one added sentence flips a required control from exit 2 to exit 0.

Also pins the two behaviors that make that take film cleanly: the pass names the
control as covered, and a system prompt never carries a config-only smell.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest
from click.testing import CliRunner

from crewscore.cli import main
from crewscore.smells import detect_smells

CONTROL = "human_gate.approval_required"
BARE = "You are a helpful assistant that answers questions.\n"
SENTENCE = "A human must approve any refund or account change before it happens.\n"

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _run(path, *extra):
    return CliRunner().invoke(
        main, ["test", "-f", str(path), "--no-explain", "--require", CONTROL, *extra]
    )


def test_one_sentence_turns_required_control_from_exit_2_to_exit_0(tmp_path):
    prompt = tmp_path / "ines-support-assistant.md"
    prompt.write_text(BARE, encoding="utf-8")

    before = _run(prompt)
    assert before.exit_code == 2
    assert "Required-control failure" in before.output
    assert "REQUIRED CONTROL COVERED" not in before.output
    assert "A human must approve" in before.output  # the first gap named on screen

    prompt.write_text(BARE + SENTENCE, encoding="utf-8")
    after = _run(prompt)
    assert after.exit_code == 0
    assert f"REQUIRED CONTROL COVERED: {CONTROL}" in after.output
    assert "not proof" in after.output


def test_hero_json_policy_lists_the_covered_control(tmp_path):
    prompt = tmp_path / "p.md"
    prompt.write_text(BARE + SENTENCE, encoding="utf-8")
    result = _run(prompt, "--json")
    assert result.exit_code == 0
    policy = json.loads(result.stdout)["policy"]
    assert policy["covered_required_controls"] == [CONTROL]
    assert policy["missing_required_controls"] == []


def _commit_all(repo, message):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-qm", message],
        cwd=repo, check=True, env=env,
    )


@needs_git
def test_system_prompt_in_single_commit_repo_has_no_init_fossilization(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    prompt = tmp_path / "ines-support-assistant.md"
    prompt.write_text(BARE + SENTENCE, encoding="utf-8")
    _commit_all(tmp_path, "init")

    result = _run(prompt)
    assert result.exit_code == 0
    assert "Init Fossilization" not in result.output

    # The same one-commit history on coding-agent config still earns the smell.
    config = tmp_path / "AGENTS.md"
    config.write_text("# Rules\n\nUse pnpm.\n", encoding="utf-8")
    _commit_all(tmp_path, "agents")
    ids = lambda **kw: {  # noqa: E731
        s["smell_id"]
        for s in detect_smells("x", path=config, repo_root=tmp_path, **kw)
    }
    assert "smell.init_fossilization" in ids()
    assert "smell.init_fossilization" not in ids(governance=True)
