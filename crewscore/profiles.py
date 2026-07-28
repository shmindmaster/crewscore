"""Artifact profiles — decide which ruleset a file should be judged by.

CrewScore judges two different kinds of file, and conflating them produced a
measurable defect.

**Coding-agent config** (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, …) tells a
coding agent how to work in a repository: build commands, conventions, project
layout. Validated against the 100-repo corpus from dos Santos et al.
(arXiv:2606.15828), the governance ruleset scores these at a **median of
0/100**, with all 100 files landing in the worst tier. That is not a finding
about the files — it is a category error. There is no reason for a build-
instructions file to carry HIPAA language or human-approval gates.

**Production system prompts** instruct an agent that acts on behalf of users:
answering, calling tools, sending, writing. Governance signals belong there.

So the profile decides the verdict:

    coding_agent_config -> configuration smells; no governance tier
    system_prompt       -> 8 governance dimensions; smells still advisory

Classification is by filename and path only. Content sniffing would be a
guess dressed up as a measurement, and getting it wrong silently is exactly
the failure this module exists to prevent. When the path is not decisive the
answer is `system_prompt` — the historical default — and `--profile` lets a
caller override any of it.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "CODING_AGENT_CONFIG",
    "SYSTEM_PROMPT",
    "PROFILES",
    "PROFILE_LABELS",
    "classify_path",
    "governance_applies",
]

CODING_AGENT_CONFIG = "coding_agent_config"
SYSTEM_PROMPT = "system_prompt"

PROFILES = (CODING_AGENT_CONFIG, SYSTEM_PROMPT)

PROFILE_LABELS = {
    CODING_AGENT_CONFIG: "coding-agent config",
    SYSTEM_PROMPT: "agent system prompt",
}

# Exact basenames that are unambiguously repo guidance for a coding agent.
_CONFIG_BASENAMES = frozenset(
    {
        "agents.md",
        "agent.md",
        "claude.md",
        "gemini.md",
        "warp.md",
        "soul.md",
        "conventions.md",  # aider
        "copilot-instructions.md",
        ".cursorrules",
        ".windsurfrules",
        ".clinerules",
        ".aider.conf.yml",
    }
)

# Cursor / Windsurf style rule files live under these directories as .mdc.
_CONFIG_DIR_NAMES = frozenset({".cursor", ".windsurf", ".clinerules", ".github"})


def classify_path(path: str | Path | None) -> str:
    """Return the profile for a path. Defaults to SYSTEM_PROMPT.

    A `--prompt` string has no path, so it is a system prompt by definition:
    nobody pastes their build instructions into a prompt scorer on purpose.
    """
    if not path:
        return SYSTEM_PROMPT

    p = Path(path)
    name = p.name.lower()

    if name in _CONFIG_BASENAMES:
        return CODING_AGENT_CONFIG

    # `.cursor/rules/*.mdc` and friends are coding-agent config regardless of
    # the leaf filename, which is usually a topic name like `testing.mdc`.
    if p.suffix.lower() == ".mdc":
        for part in p.parts[:-1]:
            if part.lower() in _CONFIG_DIR_NAMES:
                return CODING_AGENT_CONFIG

    if name == "copilot-instructions.md":
        return CODING_AGENT_CONFIG

    return SYSTEM_PROMPT


def governance_applies(profile: str) -> bool:
    """Whether the 8 governance dimensions mean anything for this profile."""
    return profile != CODING_AGENT_CONFIG
