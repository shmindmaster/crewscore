"""Open, auditable catalog of every scoring rule.

CrewScore is not a black box: the formula, ruleset id, and every regex
are exportable via this module and `crewscore rules`.
"""

from __future__ import annotations

from typing import Any

from crewscore.scoring import DIMENSIONS, RULESET_ID, overall_score, score_tier
from crewscore.scorers.structural_analysis import (
    DIMENSION_SIGNAL_LABELS,
    PATTERN_RULE_IDS,
    SCORER_MAP,
)

# Stable description of how numbers are produced (human + machine).
SCORING_METHOD: dict[str, Any] = {
    "type": "deterministic_regex",
    "llm_calls": False,
    "api_key_required": False,
    "ruleset": RULESET_ID,
    "dimension_score_formula": (
        "matches = count of rules whose regex hits the prompt (case-insensitive); "
        "if matches == 0 or total_rules == 0 → 0; "
        "else min(100, round(15 + 85 * matches / total_rules))"
    ),
    "overall_score_formula": (
        "floor(mean of the 8 dimension scores) — integer division of sum/len"
    ),
    "tier_thresholds": {
        "STRUCTURAL: STRONG": "overall >= 90",
        "STRUCTURAL: OK WITH GAPS": "70 <= overall < 90",
        "STRUCTURAL: WEAK": "50 <= overall < 70",
        "STRUCTURAL: CRITICAL GAPS": "overall < 50",
    },
    "what_this_is_not": [
        "Not live red-teaming or jailbreak proof",
        "Not runtime tool-gate enforcement",
        "Not a security or compliance certification",
        "Not proof the model will obey the text",
    ],
    "source_of_truth": "crewscore/scorers/structural_analysis.py",
    "list_rules_cli": "crewscore rules",
    "list_rules_json": "crewscore rules --json",
}


def _label_for_pattern(dimension: str, pattern: str) -> str | None:
    for p, label in DIMENSION_SIGNAL_LABELS.get(dimension, []):
        if p == pattern:
            return label
    return None


def list_rules(*, dimension: str | None = None) -> list[dict[str, Any]]:
    """Return every rule as a transparent dict (id, dimension, regex, label)."""
    rows: list[dict[str, Any]] = []
    for dim_key, patterns in SCORER_MAP.items():
        if dimension and dim_key != dimension:
            continue
        dim_label = next((lab for lab, k in DIMENSIONS if k == dim_key), dim_key)
        for rule_id, pattern in patterns:
            rows.append(
                {
                    "rule_id": rule_id,
                    "dimension": dim_key,
                    "dimension_label": dim_label,
                    "pattern": pattern,
                    "label": _label_for_pattern(dim_key, pattern),
                    "open": True,
                }
            )
    return rows


def catalog_payload(*, dimension: str | None = None) -> dict[str, Any]:
    """Full open catalog for `crewscore rules --json`."""
    rules = list_rules(dimension=dimension)
    by_dim: dict[str, int] = {}
    for r in rules:
        by_dim[r["dimension"]] = by_dim.get(r["dimension"], 0) + 1
    return {
        "ruleset": RULESET_ID,
        "method": SCORING_METHOD,
        "dimensions": [
            {"key": key, "label": label, "rule_count": by_dim.get(key, 0)}
            for label, key in DIMENSIONS
            if not dimension or key == dimension
        ],
        "rules": rules,
        "rule_count": len(rules),
        "pattern_index_size": len(PATTERN_RULE_IDS),
    }


def scoring_transparency_block() -> dict[str, Any]:
    """Compact block embedded in every JSON score result."""
    return {
        "ruleset": RULESET_ID,
        "type": SCORING_METHOD["type"],
        "formula_dimension": SCORING_METHOD["dimension_score_formula"],
        "formula_overall": SCORING_METHOD["overall_score_formula"],
        "open_rules": "crewscore rules --json",
        "source": SCORING_METHOD["source_of_truth"],
        "not": SCORING_METHOD["what_this_is_not"],
    }


def demo_formula(matches: int, total: int) -> int:
    """Public pure function documenting dimension scoring (used in tests/docs)."""
    if total == 0 or matches == 0:
        return 0
    return min(100, round(15 + 85 * (matches / total)))


# Re-export helpers tests may want
__all__ = [
    "SCORING_METHOD",
    "list_rules",
    "catalog_payload",
    "scoring_transparency_block",
    "demo_formula",
    "score_tier",
    "overall_score",
]
