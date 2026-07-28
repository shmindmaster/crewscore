"""Markdown CI summaries are transparent (rule IDs, formula, not black box)."""

from crewscore.scoring import build_result
from crewscore.summary import format_scan_markdown, format_score_markdown


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
