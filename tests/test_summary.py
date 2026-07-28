"""Markdown CI summaries are transparent (rule IDs, formula, not black box)."""

from crewscore.profiles import CODING_AGENT_CONFIG
from crewscore.scoring import build_result
from crewscore.summary import format_scan_markdown, format_score_markdown

_ZERO_DIMS = {
    k: 0
    for k in [
        "injection", "hallucination", "citation", "cost",
        "human_gate", "safe_stop", "audit", "compliance",
    ]
}


def test_config_markdown_reports_warnings():
    """The PR comment is where a no-op CI gate has to show up.

    The Action passes --threshold unconditionally (default "50"), so every
    config-file comment would otherwise omit that the gate did nothing.
    """
    result = build_result(
        dict(_ZERO_DIMS),
        profile=CODING_AGENT_CONFIG,
        warnings=["threshold_ignored_for_config"],
    )
    md = format_score_markdown(result)
    assert "threshold_ignored_for_config" in md
    assert "--max-smells" in md


def test_config_markdown_has_no_warnings_section_when_clean():
    result = build_result(dict(_ZERO_DIMS), profile=CODING_AGENT_CONFIG)
    md = format_score_markdown(result)
    assert "Warnings" not in md


def test_score_markdown_includes_formula_and_ruleset():
    result = build_result(
        {k: 0 for k in [
            "injection", "hallucination", "citation", "cost",
            "human_gate", "safe_stop", "audit", "compliance",
        ]},
        prompt_text="bare",
    )
    md = format_score_markdown(
        result,
        findings=[
            {
                "dimension": "injection",
                "status": "missing",
                "rule_id": "injection.01",
                "pattern_or_reason": "Reject override",
            }
        ],
    )
    assert "0/100" in md
    assert "crewscore-hygiene@" in md
    assert "15+85" in md or "15 + 85" in md or "matches" in md
    assert "injection.01" in md
    assert "not" in md.lower() or "Not" in md
    assert "crewscore rules" in md


def test_scan_markdown_worst_first_table():
    md = format_scan_markdown(
        [
            {"path": "a.md", "overall": 40, "tier": "STRUCTURAL: WEAK", "ruleset": "crewscore-hygiene@0.2.3"},
            {"path": "b.md", "overall": 10, "tier": "STRUCTURAL: CRITICAL GAPS", "ruleset": "crewscore-hygiene@0.2.3"},
        ]
    )
    assert "10/100" in md
    assert "b.md" in md
    assert "| Path |" in md


def test_scan_markdown_headline_ignores_coding_agent_config():
    """A config file at 0 must never become the PR comment's headline score.

    This body is the sticky PR comment and the job summary — the most public
    surface CrewScore has. Ranking AGENTS.md by the governance score puts a
    category error at the top of every comment.
    """
    md = format_scan_markdown(
        [
            {
                "path": "AGENTS.md",
                "overall": 0,
                "tier": "CONFIG: NO SMELLS DETECTED",
                "governance_applicable": False,
            },
            {
                "path": "prompts/sys.md",
                "overall": 87,
                "tier": "STRUCTURAL: OK WITH GAPS",
                "governance_applicable": True,
            },
        ]
    )
    assert "**87/100**" in md
    assert "prompts/sys.md" in md
    assert "0/100" not in md
    assert "CONFIG: NO SMELLS DETECTED" in md


def test_scan_markdown_config_row_shows_verdict_not_number():
    """Table rows for config show the smell verdict, never a 0-100 number."""
    md = format_scan_markdown(
        [
            {
                "path": "AGENTS.md",
                "overall": 0,
                "tier": "CONFIG: 2 SMELLS",
                "governance_applicable": False,
            },
            {
                "path": "prompts/sys.md",
                "overall": 87,
                "tier": "STRUCTURAL: OK WITH GAPS",
                "governance_applicable": True,
            },
        ]
    )
    config_row = next(line for line in md.splitlines() if "AGENTS.md" in line and "|" in line)
    assert "0" not in config_row
    assert "n/a" in config_row
    assert "CONFIG: 2 SMELLS" in config_row
    prompt_row = next(line for line in md.splitlines() if "prompts/sys.md" in line and "|" in line)
    assert "87" in prompt_row


def test_scan_markdown_config_only_has_no_governance_headline():
    """A repo with only AGENTS.md-class files gets a smell verdict, no grade."""
    md = format_scan_markdown(
        [
            {
                "path": "AGENTS.md",
                "overall": 0,
                "tier": "CONFIG: 1 SMELL",
                "governance_applicable": False,
            },
            {
                "path": "CLAUDE.md",
                "overall": 0,
                "tier": "CONFIG: NO SMELLS DETECTED",
                "governance_applicable": False,
            },
        ]
    )
    assert "/100" not in md
    assert "Worst score" not in md
    assert "configuration smells" in md.lower()
    assert "CONFIG: 1 SMELL" in md
    # Do not claim nothing was found directly above a table listing what was found.
    assert "No agent system prompts found" not in md
    assert "coding-agent config" in md.lower()
