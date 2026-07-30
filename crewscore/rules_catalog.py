"""Open, auditable catalog of every scoring rule.

CrewScore is not a black box: the formula, ruleset id, and every regex
are exportable via this module and `crewscore rules`.
"""

from __future__ import annotations

from typing import Any

from crewscore.scoring import DIMENSIONS, RULESET_ID, overall_score, score_tier
from crewscore.scorers.structural_analysis import (
    CONCEPTS,
    PATTERN_RULE_IDS,
    RULE_LABELS,
    SCORER_MAP,
)

# ─── Provenance ───────────────────────────────────────────────────
#
# Where each dimension's rules come from, graded honestly. The point is not to
# claim more grounding than exists — it is to let a reader see exactly which
# dimensions rest on published measurement and which rest on the author's
# judgement, and to weight their trust accordingly.
#
# Provenance is recorded per dimension, not per rule: the rules within a
# dimension share one justification, and pretending to per-regex citations
# would be false precision.

PROVENANCE_GRADES: dict[str, str] = {
    "evidence-backed": (
        "An external published measurement supports both that this failure "
        "class matters and that it is observable in instruction text."
    ),
    "plausible": (
        "Widely documented practitioner risk, but no measurement shows that "
        "prompt text mitigates it."
    ),
    "author-intuition": (
        "No external grounding beyond the author's judgement. Treat with "
        "the least confidence — and argue with us in an issue."
    ),
}

DIMENSION_PROVENANCE: dict[str, dict[str, Any]] = {
    "injection": {
        "grade": "evidence-backed",
        "rationale": (
            "Prompt injection is OWASP's top LLM risk, and cross-vendor "
            "analysis finds interference patterns detectable in system-prompt "
            "text itself."
        ),
        "citations": [
            "OWASP Top 10 for LLM Applications — LLM01 Prompt Injection",
            "Arbiter: Detecting Interference in LLM Agent System Prompts "
            "(arXiv:2603.08993)",
        ],
    },
    "safe_stop": {
        "grade": "evidence-backed",
        "rationale": (
            "Whether an agent knows when not to act is directly measured, and "
            "instruction wording has a measured effect on that behaviour."
        ),
        "citations": [
            "AgentAbstain: Do LLM Agents Know When Not to Act? "
            "(arXiv:2607.10059)",
            "Coding Agents Don't Know When to Act (arXiv:2605.07769)",
        ],
    },
    "cost": {
        "grade": "evidence-backed",
        "rationale": (
            "Inference cost from instruction text is measured, and cost is a "
            "named driver of agentic project cancellation. Patterns were "
            "tightened in 0.6.0 so gift 'budget', tool 'rate limited', and "
            "content 'truncated' no longer score as cost controls."
        ),
        "citations": [
            "Evaluating AGENTS.md (arXiv:2602.11988) — >20% inference-cost "
            "increase with no success-rate gain",
            "Gartner, 2025-06-25 — cost as an agentic-project cancellation "
            "driver",
        ],
    },
    "hallucination": {
        "grade": "plausible",
        "rationale": (
            "Fabrication is a well-documented failure mode, but no study "
            "shows that anti-hallucination wording in a system prompt "
            "reduces it."
        ),
        "citations": [],
    },
    "citation": {
        "grade": "plausible",
        "rationale": (
            "Traceability is standard practice in grounded systems; the "
            "effect of requiring it in prompt text is unmeasured."
        ),
        "citations": [],
    },
    "human_gate": {
        "grade": "plausible",
        "rationale": (
            "Over-permissioned agents and soft confirm-before-act language "
            "recur in incident write-ups, but the mitigation is a runtime "
            "tool gate. Text is at best a statement of intent."
        ),
        "citations": [],
    },
    "audit": {
        "grade": "plausible",
        "rationale": (
            "Reconstructing what an agent did is a real compliance need. "
            "Whether asking for it in a prompt produces it is unmeasured — "
            "logging is an application concern. Patterns were tightened in "
            "0.6.0 against 'TRACE every symbol', personality "
            "'accountability', and 'immutable security boundary' false "
            "positives measured on the public corpus."
        ),
        "citations": [],
    },
    "compliance": {
        "grade": "author-intuition",
        "rationale": (
            "Still the weakest dimension by design: regime names and data-"
            "protection techniques in prompt text are not lawful handling. "
            "0.6.0 dropped bare 'compliance|legal|encrypt|redact' so refusal "
            "copy and PDF tool lists no longer inflate coverage; the grade "
            "stays author-intuition because the construct remains thin."
        ),
        "citations": [],
    },
}


# Stable description of how numbers are produced (human + machine).
SCORING_METHOD: dict[str, Any] = {
    "type": "deterministic_regex",
    "llm_calls": False,
    "api_key_required": False,
    "ruleset": RULESET_ID,
    "dimension_score_formula": (
        "A dimension defines N distinct controls (concepts). A control is "
        "covered when ANY of its rules hits the prompt (case-insensitive) — "
        "rules within a control are alternative phrasings, not additive "
        "evidence. matches = controls with at least one rule hit; "
        "score = (100 * matches + N // 2) // N (integer round-half-up), "
        "or 0 when matches == 0."
    ),
    "overall_score_formula": (
        "floor(mean of the 8 dimension scores) — integer division of sum/len"
    ),
    "why_not_count_rules": (
        "Scoring matched_rules/total_rules counted synonyms as separate "
        "evidence, so stating a control once scored 24-32 while restating it "
        "six ways scored well — rewarding the redundancy the tool reports as "
        "a smell. Controls are counted once each instead."
    ),
    "list_concepts_cli": "crewscore rules --concepts",
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


def _concept_for_rule(dimension: str, rule_id: str) -> tuple[str | None, str | None]:
    """Which control this rule is one phrasing of. Drives the denominator."""
    for concept in CONCEPTS.get(dimension, ()):
        if rule_id in concept.rule_ids:
            return concept.key, concept.label
    return None, None


def list_rules(*, dimension: str | None = None) -> list[dict[str, Any]]:
    """Return every rule as a transparent dict (id, dimension, regex, label)."""
    rows: list[dict[str, Any]] = []
    for dim_key, patterns in SCORER_MAP.items():
        if dimension and dim_key != dimension:
            continue
        dim_label = next((lab for lab, k in DIMENSIONS if k == dim_key), dim_key)
        provenance = DIMENSION_PROVENANCE.get(dim_key, {})
        for rule_id, pattern in patterns:
            concept_key, concept_label = _concept_for_rule(dim_key, rule_id)
            rows.append(
                {
                    "rule_id": rule_id,
                    "dimension": dim_key,
                    "dimension_label": dim_label,
                    "pattern": pattern,
                    "label": RULE_LABELS.get(rule_id),
                    "concept": concept_key,
                    "concept_label": concept_label,
                    "open": True,
                    "provenance": provenance.get("grade", "author-intuition"),
                }
            )
    return rows


def list_concepts(*, dimension: str | None = None) -> list[dict[str, Any]]:
    """The scoring denominator, published as data.

    A dimension scores on how many of these controls the prompt states, so the
    grouping is as load-bearing as the regexes and gets the same exposure.
    """
    rows: list[dict[str, Any]] = []
    for dim_key, concepts in CONCEPTS.items():
        if dimension and dim_key != dimension:
            continue
        dim_label = next((lab for lab, k in DIMENSIONS if k == dim_key), dim_key)
        for concept in concepts:
            rows.append(
                {
                    "concept": concept.key,
                    "label": concept.label,
                    "dimension": dim_key,
                    "dimension_label": dim_label,
                    "rule_ids": list(concept.rule_ids),
                    "points": round(100 / len(concepts)),
                }
            )
    return rows


def catalog_payload(*, dimension: str | None = None) -> dict[str, Any]:
    """Full open catalog for `crewscore rules --json`."""
    rules = list_rules(dimension=dimension)
    concepts = list_concepts(dimension=dimension)
    by_dim: dict[str, int] = {}
    for r in rules:
        by_dim[r["dimension"]] = by_dim.get(r["dimension"], 0) + 1
    concepts_by_dim: dict[str, int] = {}
    for c in concepts:
        concepts_by_dim[c["dimension"]] = concepts_by_dim.get(c["dimension"], 0) + 1
    return {
        "ruleset": RULESET_ID,
        "method": SCORING_METHOD,
        "provenance_grades": PROVENANCE_GRADES,
        "dimensions": [
            {
                "key": key,
                "label": label,
                "rule_count": by_dim.get(key, 0),
                # The scoring denominator for this dimension.
                "control_count": concepts_by_dim.get(key, 0),
                **DIMENSION_PROVENANCE.get(key, {}),
            }
            for label, key in DIMENSIONS
            if not dimension or key == dimension
        ],
        "concepts": concepts,
        "control_count": len(concepts),
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


def demo_formula(covered_controls: int, total_controls: int) -> int:
    """Public pure function documenting dimension scoring (used in tests/docs).

    Thin re-export of the implementation rather than a second copy of the
    arithmetic: the previous duplicate is how the published formula and the
    code drifted apart once already.
    """
    from crewscore.scorers.structural_analysis import score_from_concepts

    return score_from_concepts(covered_controls, total_controls)


# Re-export helpers tests may want
__all__ = [
    "SCORING_METHOD",
    "list_rules",
    "list_concepts",
    "catalog_payload",
    "scoring_transparency_block",
    "demo_formula",
    "score_tier",
    "overall_score",
]
