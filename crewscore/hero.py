"""Hero missing-control + control-coverage N/23 share language.

The governance number is coverage of written controls, not a quality ranking.
This module surfaces one shareable "hero" gap (highest-priority missing control)
and honest N/23 wording for viral / CI surfaces.
"""

from __future__ import annotations

from crewscore.scorers.structural_analysis import CONCEPT_COUNT, analyze_with_findings

# Priority for viral wedge (first missing wins).
HERO_PRIORITY: list[str] = [
    "human_gate.approval_required",
    "injection.override_resistance",
    "injection.named_defense",
    "safe_stop.stop_condition",
    "safe_stop.uncertainty_trigger",
    "hallucination.no_fabrication",
    "citation.require",
    "cost.budget_cap",
    "audit.log_actions",
    "compliance.named_regime",
]

_HOMEPAGE = "https://crewscore.ai"


def coverage_from_findings(findings: list[dict]) -> tuple[int, int]:
    """Return (matched_controls, total_controls). total must equal CONCEPT_COUNT (23)."""
    matched = sum(1 for f in findings if f.get("status") == "matched")
    total = CONCEPT_COUNT
    return matched, total


def hero_missing_control(findings: list[dict]) -> dict | None:
    """Return the highest-priority missing control finding, or first missing, or None.

    Returned dict includes at least: concept, label (from pattern_or_reason),
    dimension, and rule_id if present.
    """
    missing = [f for f in findings if f.get("status") == "missing"]
    if not missing:
        return None

    by_concept = {f.get("concept"): f for f in missing if f.get("concept")}
    chosen = None
    for key in HERO_PRIORITY:
        if key in by_concept:
            chosen = by_concept[key]
            break
    if chosen is None:
        chosen = missing[0]

    return _normalize_hero(chosen)


def _normalize_hero(finding: dict) -> dict:
    """Shape a finding into the public hero payload."""
    out: dict = {
        "concept": finding.get("concept"),
        "label": finding.get("pattern_or_reason") or finding.get("label"),
        "dimension": finding.get("dimension"),
    }
    if finding.get("rule_id"):
        out["rule_id"] = finding["rule_id"]
    # Keep pattern_or_reason for callers that read the raw findings key.
    if finding.get("pattern_or_reason") is not None:
        out["pattern_or_reason"] = finding["pattern_or_reason"]
    return out


def coverage_summary(prompt: str) -> dict:
    """Run analyze_with_findings and return coverage + hero + share helpers."""
    _scores, findings = analyze_with_findings(prompt)
    matched, total = coverage_from_findings(findings)
    missing = total - matched
    hero = hero_missing_control(findings)

    share_line = _share_line(matched, total, hero)
    require_cli = None
    if hero and hero.get("concept"):
        require_cli = f"crewscore scan . --require {hero['concept']}"

    return {
        "matched": matched,
        "total": total,
        "missing": missing,
        "hero": hero,
        "share_line": share_line,
        "require_cli": require_cli,
    }


def _share_line(matched: int, total: int, hero: dict | None) -> str:
    """One-line shareable, honest coverage string (ASCII only)."""
    base = f"Control coverage {matched}/{total} written"
    if hero and hero.get("label"):
        base = f"{base} · missing: {hero['label']}"
    return (
        f"{base} · offline checklist (not runtime proof). {_HOMEPAGE}"
    )
