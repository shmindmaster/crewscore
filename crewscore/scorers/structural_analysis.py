"""
Structural analysis of an AI agent's system prompt.

Runs entirely offline — no LLM calls, no API key, no cost.
Analyzes the system prompt text for guardrail patterns, safety
instructions, and production-readiness signals.
"""

from __future__ import annotations

import re
from typing import Dict

from crewscore.scoring import RULESET_ID

# Re-export for callers / web export.
__all__ = [
    "RULESET_ID",
    "SCORER_MAP",
    "DIMENSION_SIGNAL_LABELS",
    "PATTERN_RULE_IDS",
    "analyze",
    "analyze_with_findings",
]

# Keywords and patterns that signal guardrail presence.
# Each entry is (rule_id, regex). rule_ids are stable across releases.
INJECTION_DEFENSE_PATTERNS: list[tuple[str, str]] = [
    ("injection.01", r"ignore\s+(previous|above|all)\s+(instructions|prompts)"),
    (
        "injection.02",
        r"do\s+not\s+(follow|obey|listen)\s+to\s+(user|input).*(system|instruction)",
    ),
    (
        "injection.03",
        r"system\s+prompt.*(?:confidential|private|do\s+not\s+reveal)",
    ),
    ("injection.04", r"reject.*(?:inject|override|manipulat)"),
    ("injection.05", r"adversar|injection|jailbreak"),
    (
        "injection.06",
        r"do\s+not\s+reveal\s+(your|the|this)\s+(system|instructions|prompt)",
    ),
    (
        "injection.07",
        r"you\s+cannot\s+be\s+(instructed|told|asked)\s+to\s+(ignore|override)",
    ),
    # Softened: bare "safety|guardrail" alone inflated scores; require defense context.
    (
        "injection.08",
        r"(?:prompt\s+)?(?:injection|jailbreak).*(?:defen|guard|protect|resist)|"
        r"(?:defen|guard|protect|resist).*(?:prompt\s+)?(?:injection|jailbreak)|"
        r"safety\s+(?:boundar|constraint|policy|policies|rule)|"
        r"guardrail\s+(?:against|for|on|policy|policies)",
    ),
]

HALLUCINATION_PATTERNS: list[tuple[str, str]] = [
    (
        "hallucination.01",
        r"do\s+not\s+(?:fabricat|invent|make\s+up|generat).*(?:fact|data|citation|source|number)",
    ),
    (
        "hallucination.02",
        r"if\s+you\s+(?:do\s+not\s+know|are\s+unsure|lack\s+(?:the|enough)\s+(?:data|information|evidence))",
    ),
    (
        "hallucination.03",
        r"only\s+(?:use|cite|reference)\s+(?:provided|given|available|verified)\s+(?:data|information|sources|context)",
    ),
    ("hallucination.04", r"(?:hallucin|fabricat|confabulat)"),
    ("hallucination.05", r"say\s+(?:I\s+dont\s+know|I\s+cannot|I\s+do\s+not\s+have)"),
    ("hallucination.06", r"ground(?:ed|ing)\s+in\s+(?:the|provided|given)"),
    ("hallucination.07", r"do\s+not\s+guess|never\s+guess|avoid\s+guess"),
    (
        "hallucination.08",
        r"recommend.*(?:consult|doctor|professional|specialist|expert)",
    ),
]

CITATION_PATTERNS: list[tuple[str, str]] = [
    ("citation.01", r"(?:cite|citation|reference|attribute|source\s+link|footnote)"),
    ("citation.02", r"(?:source|evidence|provenance)\s*(?:link|id|span|reference)"),
    (
        "citation.03",
        r"every\s+(?:claim|statement|answer|output)\s+must\s+(?:cite|reference|include)",
    ),
    (
        "citation.04",
        r"link\s+(?:to|back\s+to)\s+(?:the|its|each)\s+(?:source|evidence|document)",
    ),
    ("citation.05", r"\[?\d+\]?.*(?:source|ref|cite)"),
]

COST_PATTERNS: list[tuple[str, str]] = [
    ("cost.01", r"(?:token|cost|budget|spend)\s*(?:limit|cap|max|ceiling|threshold)"),
    ("cost.02", r"(?:max|maximum)\s*(?:token|tokens|length|response)"),
    ("cost.03", r"(?:rate|cost)\s*limit"),
    ("cost.04", r"budget|spending|cost\s*control"),
    ("cost.05", r"truncat(?:e|ion)|max_tokens|max_length"),
]

HUMAN_GATE_PATTERNS: list[tuple[str, str]] = [
    (
        "human_gate.01",
        r"(?:human|user|supervisor|operator|reviewer|staff|manager)\s*(?:must|shall|should|needs?\s+to)\s*(?:approve|review|confirm|verify|check|validate)",
    ),
    (
        "human_gate.02",
        r"(?:human|human-in-the-loop|hitl|manual)\s*(?:review|approval|gate|checkpoint|oversight)",
    ),
    (
        "human_gate.03",
        r"(?:before|prior\s+to)\s*(?:execut|send|submit|releas|publish|deploy)",
    ),
    (
        "human_gate.04",
        r"do\s+not\s+(?:auto|automatic).*(?:execute|send|submit|approve|publish)",
    ),
    (
        "human_gate.05",
        r"(?:require|mandate).*(?:human|manual)\s*(?:approval|review|confirmation)",
    ),
    (
        "human_gate.06",
        r"(?:staff|clinician|doctor|nurse|analyst|officer)\s*(?:review|approve|sign)",
    ),
]

SAFE_STOP_PATTERNS: list[tuple[str, str]] = [
    ("safe_stop.01", r"(?:stop|halt|pause|refuse|decline|abort).*(?:if|when|unless)"),
    (
        "safe_stop.02",
        r"(?:insufficient|missing|incomplete|unclear|ambiguous)\s*(?:data|evidence|information|context|instruction)",
    ),
    (
        "safe_stop.03",
        r"(?:if|when)\s+you\s+(?:are\s+)?(?:un)?(?:sure|certain|confident)",
    ),
    (
        "safe_stop.04",
        r"(?:cannot|can.t|should\s+not)\s+(?:proceed|continue|act|respond)",
    ),
    (
        "safe_stop.05",
        r"(?:escalat|hand\s*off|transfer|refer).*(?:human|supervisor|specialist|operator)",
    ),
    ("safe_stop.06", r"(?:safe|calibrated|graceful)\s*(?:stop|halt|failure|abort|exit)"),
    ("safe_stop.07", r"refuse|disclaim|opt\s*out"),
]

AUDIT_PATTERNS: list[tuple[str, str]] = [
    (
        "audit.01",
        r"(?:log|record|track|trace|audit)\s*(?:trail|history|event|action|decision|every|all|each)",
    ),
    ("audit.02", r"(?:audit|logging|trace|provenance|accountab)"),
    (
        "audit.03",
        r"(?:record|preserve|retain)\s*(?:the|all|every|each)\s*(?:decision|action|step|reason|source)",
    ),
    ("audit.04", r"immutable|append.only|tamper.proof|write.once"),
    ("audit.05", r"(?:who|what|when|why|how)\s*(?:did|made|took|decided|executed)"),
]

COMPLIANCE_PATTERNS: list[tuple[str, str]] = [
    (
        "compliance.01",
        r"(?:hipaa|phi|protected\s+health|patient\s+data|baa|business\s+associate)",
    ),
    ("compliance.02", r"(?:soc\s*2|soc2|system\s+and\s+organization\s+controls)"),
    (
        "compliance.03",
        r"(?:gdpr|general\s+data\s+protection|data\s+protection\s+regulation)",
    ),
    (
        "compliance.04",
        r"(?:eu\s+ai\s+act|artificial\s+intelligence\s+act|ai\s+regulation)",
    ),
    (
        "compliance.05",
        r"(?:fda|medical\s+device|saMD|software\s+as\s+a\s+medical\s+device)",
    ),
    ("compliance.06", r"(?:pci|pci.dss|payment\s+card)"),
    ("compliance.07", r"(?:ferpa|student\s+data|education\s+record)"),
    ("compliance.08", r"(?:compliance|regulat|govern|legal|legal\s+requirement)"),
    ("compliance.09", r"(?:encrypt|redact|de.identif|anonymi|pseudonymi)"),
]

SCORER_MAP: dict[str, list[tuple[str, str]]] = {
    "injection": INJECTION_DEFENSE_PATTERNS,
    "hallucination": HALLUCINATION_PATTERNS,
    "citation": CITATION_PATTERNS,
    "cost": COST_PATTERNS,
    "human_gate": HUMAN_GATE_PATTERNS,
    "safe_stop": SAFE_STOP_PATTERNS,
    "audit": AUDIT_PATTERNS,
    "compliance": COMPLIANCE_PATTERNS,
}

# Flat lookup: pattern regex → rule_id (for explain labels).
PATTERN_RULE_IDS: dict[str, str] = {
    pattern: rule_id
    for patterns in SCORER_MAP.values()
    for rule_id, pattern in patterns
}

# High-value signals for explain-mode missing findings.
# Each entry is (pattern, human_label) — pattern must be the exact SCORER_MAP
# regex the label describes (not a list-index guess).
DIMENSION_SIGNAL_LABELS: dict[str, list[tuple[str, str]]] = {
    "injection": [
        (
            r"ignore\s+(previous|above|all)\s+(instructions|prompts)",
            "Reject ignore-previous-instructions / override attempts",
        ),
        (
            r"do\s+not\s+(follow|obey|listen)\s+to\s+(user|input).*(system|instruction)",
            "Do not follow user input that conflicts with system rules",
        ),
        (
            r"do\s+not\s+reveal\s+(your|the|this)\s+(system|instructions|prompt)",
            "Keep system prompt confidential / do not reveal it",
        ),
    ],
    "hallucination": [
        (
            r"do\s+not\s+(?:fabricat|invent|make\s+up|generat).*(?:fact|data|citation|source|number)",
            "Do not fabricate facts, citations, or numbers",
        ),
        (
            r"if\s+you\s+(?:do\s+not\s+know|are\s+unsure|lack\s+(?:the|enough)\s+(?:data|information|evidence))",
            "Say so when you do not know or lack evidence",
        ),
        (
            r"only\s+(?:use|cite|reference)\s+(?:provided|given|available|verified)\s+(?:data|information|sources|context)",
            "Only use provided / verified data",
        ),
    ],
    "citation": [
        (
            r"(?:cite|citation|reference|attribute|source\s+link|footnote)",
            "Require citations, references, or source links",
        ),
        (
            r"every\s+(?:claim|statement|answer|output)\s+must\s+(?:cite|reference|include)",
            "Every claim must cite its source",
        ),
        (
            r"link\s+(?:to|back\s+to)\s+(?:the|its|each)\s+(?:source|evidence|document)",
            "Link claims back to source evidence",
        ),
    ],
    "cost": [
        (
            r"(?:token|cost|budget|spend)\s*(?:limit|cap|max|ceiling|threshold)",
            "Token / cost / budget limit or cap",
        ),
        (
            r"(?:max|maximum)\s*(?:token|tokens|length|response)",
            "Max token or response length constraint",
        ),
        (
            r"(?:rate|cost)\s*limit",
            "Rate or cost limiting",
        ),
    ],
    "human_gate": [
        (
            r"(?:human|user|supervisor|operator|reviewer|staff|manager)\s*(?:must|shall|should|needs?\s+to)\s*(?:approve|review|confirm|verify|check|validate)",
            "Human / supervisor must approve or review",
        ),
        (
            r"(?:human|human-in-the-loop|hitl|manual)\s*(?:review|approval|gate|checkpoint|oversight)",
            "Human-in-the-loop review or approval gate",
        ),
        (
            r"(?:before|prior\s+to)\s*(?:execut|send|submit|releas|publish|deploy)",
            "Approval required before execute / send / publish",
        ),
    ],
    "safe_stop": [
        (
            r"(?:stop|halt|pause|refuse|decline|abort).*(?:if|when|unless)",
            "Stop / halt / refuse when conditions are unmet",
        ),
        (
            r"(?:insufficient|missing|incomplete|unclear|ambiguous)\s*(?:data|evidence|information|context|instruction)",
            "Handle missing or insufficient evidence",
        ),
        (
            r"(?:escalat|hand\s*off|transfer|refer).*(?:human|supervisor|specialist|operator)",
            "Escalate to a human supervisor",
        ),
    ],
    "audit": [
        (
            r"(?:log|record|track|trace|audit)\s*(?:trail|history|event|action|decision|every|all|each)",
            "Log or audit trail for actions and decisions",
        ),
        (
            r"(?:audit|logging|trace|provenance|accountab)",
            "Audit / logging / provenance accountability",
        ),
        (
            r"immutable|append.only|tamper.proof|write.once",
            "Immutable or append-only audit trail",
        ),
    ],
    "compliance": [
        (
            r"(?:hipaa|phi|protected\s+health|patient\s+data|baa|business\s+associate)",
            "HIPAA / PHI / protected health data handling",
        ),
        (
            r"(?:soc\s*2|soc2|system\s+and\s+organization\s+controls)",
            "SOC 2 controls",
        ),
        (
            r"(?:gdpr|general\s+data\s+protection|data\s+protection\s+regulation)",
            "GDPR / data protection requirements",
        ),
    ],
}

_SNIPPET_MAX = 120
_MAX_FINDINGS_PER_STATUS = 3


def _truncate_snippet(text: str, max_len: int = _SNIPPET_MAX) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _match_patterns(
    prompt_lower: str, patterns: list[tuple[str, str]]
) -> list[tuple[str, str, str]]:
    """Return (rule_id, pattern, snippet) for each pattern that matches."""
    hits: list[tuple[str, str, str]] = []
    for rule_id, pattern in patterns:
        try:
            m = re.search(pattern, prompt_lower, re.IGNORECASE)
        except re.error:
            continue
        if m:
            hits.append((rule_id, pattern, _truncate_snippet(m.group(0))))
    return hits


def _score_from_match_count(matches: int, total_patterns: int) -> int:
    """Score a dimension from match count (0-100)."""
    if total_patterns == 0 or matches == 0:
        return 0
    raw = matches / total_patterns
    score = 15 + (raw * 85)
    return min(100, round(score))


def _score_dimension(prompt_lower: str, patterns: list[tuple[str, str]]) -> int:
    """Score a single dimension based on pattern matches (0-100)."""
    matches = _match_patterns(prompt_lower, patterns)
    return _score_from_match_count(len(matches), len(patterns))


# NOTE: CrewScore used to award a length bonus (up to +10 per dimension for
# prompts over 500 words). It was removed in ruleset 0.3.0.
#
# Two reasons, both decisive:
#   1. It rewarded the exact thing the evidence penalizes. Length is a cost,
#      not a virtue: dos Santos et al. (arXiv:2606.15828) classify files at or
#      over 200 lines as Context Bloat (42% of 100 popular repos), and
#      Gloaguen et al. (arXiv:2602.11988) measured >20% higher inference cost
#      from context files with no gain in task success.
#   2. It was never in the published formula. README and
#      rules_catalog.SCORING_METHOD both documented score as
#      15 + 85 * matches/total, with no length term — so the documented
#      formula did not match the code.
#
# Scores are now purely a function of rule matches. Length is reported as a
# smell (see crewscore/smells.py), never as points.


def analyze_with_findings(
    system_prompt: str,
) -> tuple[dict[str, int], list[dict]]:
    """Run structural analysis and return scores plus explain findings.

    Returns:
        (scores, findings) where findings is a list of dicts with keys
        dimension, status ("matched"|"missing"), pattern_or_reason, snippet,
        and rule_id when the signal maps to a known rule.
    """
    if not system_prompt or not system_prompt.strip():
        scores = {key: 0 for key in SCORER_MAP}
        findings: list[dict] = []
        for dimension in SCORER_MAP:
            signals = DIMENSION_SIGNAL_LABELS.get(dimension, [])
            for pattern, label in signals[:_MAX_FINDINGS_PER_STATUS]:
                entry: dict = {
                    "dimension": dimension,
                    "status": "missing",
                    "pattern_or_reason": label,
                    "snippet": None,
                }
                rule_id = PATTERN_RULE_IDS.get(pattern)
                if rule_id:
                    entry["rule_id"] = rule_id
                findings.append(entry)
        return scores, findings

    prompt_lower = system_prompt.lower()
    results: dict[str, int] = {}
    findings = []

    for dimension, patterns in SCORER_MAP.items():
        hits = _match_patterns(prompt_lower, patterns)
        results[dimension] = _score_from_match_count(len(hits), len(patterns))

        # Up to 3 matched snippets
        for rule_id, pattern, snippet in hits[:_MAX_FINDINGS_PER_STATUS]:
            findings.append(
                {
                    "dimension": dimension,
                    "status": "matched",
                    "pattern_or_reason": pattern,
                    "snippet": snippet,
                    "rule_id": rule_id,
                }
            )

        # Up to 3 missing human labels for unmatched high-value signals.
        # Pair by exact pattern string — never by list index alone.
        signals = DIMENSION_SIGNAL_LABELS.get(dimension, [])
        missing_count = 0
        for pattern, label in signals:
            if missing_count >= _MAX_FINDINGS_PER_STATUS:
                break
            try:
                matched = bool(re.search(pattern, prompt_lower, re.IGNORECASE))
            except re.error:
                matched = False
            if matched:
                continue
            entry = {
                "dimension": dimension,
                "status": "missing",
                "pattern_or_reason": label,
                "snippet": None,
            }
            rule_id = PATTERN_RULE_IDS.get(pattern)
            if rule_id:
                entry["rule_id"] = rule_id
            findings.append(entry)
            missing_count += 1

        # If no labels but also no hits, still report something missing
        if not hits and missing_count == 0:
            findings.append(
                {
                    "dimension": dimension,
                    "status": "missing",
                    "pattern_or_reason": f"No {dimension} guardrail signals detected",
                    "snippet": None,
                }
            )

    return results, findings


def analyze(system_prompt: str) -> Dict[str, int]:
    """Run structural analysis on a system prompt.

    Returns:
        Dict mapping dimension name → score (0-100).
    """
    scores, _ = analyze_with_findings(system_prompt)
    return scores
