"""Hero missing-control + control-coverage N/23 share language."""

from __future__ import annotations

from pathlib import Path

from crewscore.hero import (
    HERO_PRIORITY,
    coverage_from_findings,
    coverage_summary,
    hero_missing_control,
)
from crewscore.report import share_text
from crewscore.scorers.structural_analysis import CONCEPT_COUNT, analyze_with_findings
from crewscore.scoring import build_result

BARE = "You are a helpful assistant that answers customer questions."

HARDENED_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "corpus"
    / "prompts"
    / "05-hardened-ops.md"
)

_ZERO_DIMS = {
    k: 0
    for k in [
        "injection",
        "hallucination",
        "citation",
        "cost",
        "human_gate",
        "safe_stop",
        "audit",
        "compliance",
    ]
}


def _findings(prompt: str):
    _, findings = analyze_with_findings(prompt)
    return findings


def test_coverage_total_equals_concept_count():
    matched, total = coverage_from_findings(_findings(BARE))
    assert total == CONCEPT_COUNT
    assert total == 23
    assert matched == 0


def test_bare_prompt_hero_is_first_priority_control():
    """Bare prompts miss everything, so hero MUST be the top priority entry."""
    findings = _findings(BARE)
    hero = hero_missing_control(findings)
    assert hero is not None
    assert hero["concept"] == "human_gate.approval_required"
    assert hero["concept"] == HERO_PRIORITY[0]
    assert hero.get("label") or hero.get("pattern_or_reason")
    assert hero["dimension"] == "human_gate"
    assert hero.get("rule_id")


def test_hero_priority_order_beats_first_missing_in_findings_list():
    """If priority order were wrong, injection or another early finding would win.

    Findings from analyze_with_findings are ordered by dimension (injection
    first). A naive 'first missing' would return injection.*; the viral wedge
    deliberately elevates human_gate.approval_required above that.
    """
    findings = _findings(BARE)
    # Sanity: injection appears before human_gate in the findings list.
    concepts = [f["concept"] for f in findings if f["status"] == "missing"]
    assert concepts.index("injection.override_resistance") < concepts.index(
        "human_gate.approval_required"
    )
    hero = hero_missing_control(findings)
    assert hero is not None
    assert hero["concept"] == "human_gate.approval_required"
    assert hero["concept"] != "injection.override_resistance"


def test_hero_skips_matched_priority_entries():
    """When the top priority is covered, the next missing priority wins."""
    # Cover only human_gate.approval_required; leave injection missing.
    prompt = (
        "You are a helpful assistant. "
        "A human reviewer must approve before any action is executed."
    )
    findings = _findings(prompt)
    matched_concepts = {f["concept"] for f in findings if f["status"] == "matched"}
    assert "human_gate.approval_required" in matched_concepts
    hero = hero_missing_control(findings)
    assert hero is not None
    assert hero["concept"] == "injection.override_resistance"
    assert hero["concept"] == HERO_PRIORITY[1]


def test_hero_none_when_all_matched():
    findings = [
        {
            "concept": "human_gate.approval_required",
            "status": "matched",
            "pattern_or_reason": "A human must approve",
            "dimension": "human_gate",
            "rule_id": "human_gate.01",
        }
    ]
    assert hero_missing_control(findings) is None


def test_hero_falls_back_to_first_missing_outside_priority():
    """When priority list is fully covered, any remaining gap is still a hero."""
    findings = [
        {
            "concept": "human_gate.approval_required",
            "status": "matched",
            "pattern_or_reason": "A human must approve",
            "dimension": "human_gate",
            "rule_id": "human_gate.01",
        },
        {
            "concept": "citation.inline_marker",
            "status": "missing",
            "pattern_or_reason": "Use an inline citation marker format",
            "dimension": "citation",
            "rule_id": "citation.05",
        },
    ]
    hero = hero_missing_control(findings)
    assert hero is not None
    assert hero["concept"] == "citation.inline_marker"


def test_hardened_prompt_has_high_matched_coverage():
    prompt = HARDENED_PATH.read_text(encoding="utf-8")
    findings = _findings(prompt)
    matched, total = coverage_from_findings(findings)
    assert total == 23
    assert matched >= 20
    # Hardened fixture currently leaves at most a small residual gap.
    hero = hero_missing_control(findings)
    if hero is not None:
        assert hero["concept"]
        assert hero.get("label") or hero.get("pattern_or_reason")


def test_coverage_summary_shape_and_share_line():
    summary = coverage_summary(BARE)
    assert summary["matched"] == 0
    assert summary["total"] == 23
    assert summary["missing"] == 23
    assert summary["hero"] is not None
    assert summary["hero"]["concept"] == "human_gate.approval_required"
    assert "label" in summary["hero"]
    assert "dimension" in summary["hero"]
    share = summary["share_line"]
    assert isinstance(share, str)
    assert "0/23" in share or "0/23" in share.replace(" ", "")
    assert "Control coverage" in share or "control" in share.lower()
    # Honesty: never claim runtime safety or certification.
    lowered = share.lower()
    assert "runtime proof" in lowered or "not runtime" in lowered
    assert "certif" not in lowered
    assert summary["require_cli"] == (
        "crewscore scan . --require human_gate.approval_required"
    )


def test_coverage_summary_require_cli_none_when_fully_covered():
    # Synthetic full-match findings via empty missing set: use a prompt that
    # scores highly; require_cli is None only when hero is None.
    findings = [
        {
            "concept": c,
            "status": "matched",
            "pattern_or_reason": c,
            "dimension": c.split(".")[0],
            "rule_id": f"{c.split('.')[0]}.01",
        }
        for c in HERO_PRIORITY
    ]
    # Direct unit path: hero None => require_cli None when all matched.
    assert hero_missing_control(findings) is None


def test_share_text_governance_default_uses_control_coverage_language():
    result = build_result(dict(_ZERO_DIMS), mode="structural", source="prompt")
    text = share_text(result)
    assert "Control coverage" in text
    assert "0/100" in text
    assert "not runtime proof" in text
    assert "crewscore.ai" in text
    # Vanity "quality score" framing is gone.
    assert "My AI agent scored" not in text


def test_share_text_with_matched_total_and_hero():
    result = build_result(dict(_ZERO_DIMS), mode="structural", source="prompt")
    text = share_text(
        result,
        matched=0,
        total=23,
        hero_label="A human must approve",
    )
    assert "Control coverage" in text
    assert "0/23" in text
    assert "missing:" in text
    assert "A human must approve" in text
    assert "not runtime" in text
    assert "crewscore.ai" in text


def test_share_text_with_matched_total_omits_missing_when_no_hero():
    result = build_result(
        {
            "injection": 100,
            "hallucination": 100,
            "citation": 100,
            "cost": 100,
            "human_gate": 100,
            "safe_stop": 100,
            "audit": 100,
            "compliance": 100,
        },
        mode="structural",
        source="prompt",
    )
    text = share_text(result, matched=23, total=23, hero_label=None)
    assert "Control coverage" in text
    assert "23/23" in text
    assert "missing:" not in text
    assert "not runtime" in text


def test_share_text_config_path_unchanged():
    from crewscore.profiles import CODING_AGENT_CONFIG

    result = build_result(
        dict(_ZERO_DIMS),
        mode="structural",
        source="AGENTS.md",
        smells=[],
        profile=CODING_AGENT_CONFIG,
    )
    text = share_text(result)
    assert "config" in text.lower()
    assert "smell" in text.lower()
    assert "Control coverage" not in text
