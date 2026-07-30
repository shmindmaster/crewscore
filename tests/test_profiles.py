"""Artifact profile classification (crewscore/profiles.py)."""

import pytest

from crewscore.profiles import (
    CODING_AGENT_CONFIG,
    SYSTEM_PROMPT,
    classify_path,
    governance_applies,
)
from crewscore.scoring import build_result, config_tier
from crewscore.scorers.structural_analysis import analyze


@pytest.mark.parametrize(
    "path",
    [
        "AGENTS.md",
        "agents.md",
        "CLAUDE.md",
        "GEMINI.md",
        "WARP.md",
        ".cursorrules",
        ".windsurfrules",
        "CONVENTIONS.md",
        "repo/sub/AGENTS.md",
        ".github/copilot-instructions.md",
        ".cursor/rules/testing.mdc",
        ".cursor/rules/conventions.md",  # rules dir, not only .mdc
        ".windsurf/rules/style.md",
    ],
)
def test_coding_agent_config_is_recognised(path):
    assert classify_path(path) == CODING_AGENT_CONFIG


@pytest.mark.parametrize(
    "path",
    [
        "system-prompt.md",
        "prompts/support-agent.md",
        "agents/triage/system.md",
        "my-agent/instructions.txt",
        "docs/notes.mdc",  # .mdc outside a config dir is not config
        ".cursor/commands/snippet.md",  # Cursor slash commands are not config rules
    ],
)
def test_system_prompts_stay_governed(path):
    assert classify_path(path) == SYSTEM_PROMPT


def test_pasted_string_defaults_to_system_prompt():
    """--prompt has no path; nobody pastes build instructions on purpose."""
    assert classify_path(None) == SYSTEM_PROMPT


def test_governance_applies_only_to_prompts():
    assert governance_applies(SYSTEM_PROMPT) is True
    assert governance_applies(CODING_AGENT_CONFIG) is False


def test_config_profile_gets_a_smell_verdict_not_a_grade():
    """A config file must never be handed a 0-100 governance verdict."""
    text = "# Guide\n\nAlways use pnpm. Build with `make build`.\n"
    result = build_result(
        analyze(text), profile=CODING_AGENT_CONFIG, prompt_text=text
    )
    assert result.governance_applicable is False
    assert result.tier == "CONFIG: NO SMELLS DETECTED"
    assert "STRUCTURAL" not in result.tier


def test_config_tier_counts_smells():
    assert config_tier(0) == "CONFIG: NO SMELLS DETECTED"
    assert config_tier(1) == "CONFIG: 1 SMELL"
    assert config_tier(3) == "CONFIG: 3 SMELLS"


def test_prompt_profile_keeps_the_structural_tier():
    text = "You are a helpful assistant."
    result = build_result(analyze(text), profile=SYSTEM_PROMPT, prompt_text=text)
    assert result.governance_applicable is True
    assert result.tier.startswith("STRUCTURAL:")


def test_profile_round_trips_through_json():
    result = build_result({}, profile=CODING_AGENT_CONFIG)
    payload = result.to_dict()
    assert payload["profile"] == CODING_AGENT_CONFIG
    assert payload["governance_applicable"] is False
