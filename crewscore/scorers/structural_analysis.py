"""
Structural analysis of an AI agent's system prompt.

Runs entirely offline — no LLM calls, no API key, no cost.
Analyzes the system prompt text for guardrail patterns, safety
instructions, and production-readiness signals.
"""

from __future__ import annotations

import re
from typing import Dict

# Keywords and patterns that signal guardrail presence
INJECTION_DEFENSE_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+(instructions|prompts)",
    r"do\s+not\s+(follow|obey|listen)\s+to\s+(user|input).*(system|instruction)",
    r"system\s+prompt.*(?:confidential|private|do\s+not\s+reveal)",
    r"reject.*(?:inject|override|manipulat)",
    r"adversar|injection|jailbreak",
    r"do\s+not\s+reveal\s+(your|the|this)\s+(system|instructions|prompt)",
    r"you\s+cannot\s+be\s+(instructed|told|asked)\s+to\s+(ignore|override)",
    r"safety|guardrail|boundar",
]

HALLUCINATION_PATTERNS = [
    r"do\s+not\s+(?:fabricat|invent|make\s+up|generat).*(?:fact|data|citation|source|number)",
    r"if\s+you\s+(?:do\s+not\s+know|are\s+unsure|lack\s+(?:the|enough)\s+(?:data|information|evidence))",
    r"only\s+(?:use|cite|reference)\s+(?:provided|given|available|verified)\s+(?:data|information|sources|context)",
    r"(?:hallucin|fabricat|confabulat)",
    r"say\s+(?:I\s+dont\s+know|I\s+cannot|I\s+do\s+not\s+have)",
    r"ground(?:ed|ing)\s+in\s+(?:the|provided|given)",
    r"do\s+not\s+guess|never\s+guess|avoid\s+guess",
    r"recommend.*(?:consult|doctor|professional|specialist|expert)",
]

CITATION_PATTERNS = [
    r"(?:cite|citation|reference|attribute|source\s+link|footnote)",
    r"(?:source|evidence|provenance)\s*(?:link|id|span|reference)",
    r"every\s+(?:claim|statement|answer|output)\s+must\s+(?:cite|reference|include)",
    r"link\s+(?:to|back\s+to)\s+(?:the|its|each)\s+(?:source|evidence|document)",
    r"\[?\d+\]?.*(?:source|ref|cite)",
]

COST_PATTERNS = [
    r"(?:token|cost|budget|spend)\s*(?:limit|cap|max|ceiling|threshold)",
    r"(?:max|maximum)\s*(?:token|tokens|length|response)",
    r"(?:rate|cost)\s*limit",
    r"budget|spending|cost\s*control",
    r"truncat(?:e|ion)|max_tokens|max_length",
]

HUMAN_GATE_PATTERNS = [
    r"(?:human|user|supervisor|operator|reviewer|staff|manager)\s*(?:must|shall|should|needs?\s+to)\s*(?:approve|review|confirm|verify|check|validate)",
    r"(?:human|human-in-the-loop|hitl|manual)\s*(?:review|approval|gate|checkpoint|oversight)",
    r"(?:before|prior\s+to)\s*(?:execut|send|submit|releas|publish|deploy)",
    r"do\s+not\s+(?:auto|automatic).*(?:execute|send|submit|approve|publish)",
    r"(?:require|mandate).*(?:human|manual)\s*(?:approval|review|confirmation)",
    r"(?:staff|clinician|doctor|nurse|analyst|officer)\s*(?:review|approve|sign)",
]

SAFE_STOP_PATTERNS = [
    r"(?:stop|halt|pause|refuse|decline|abort).*(?:if|when|unless)",
    r"(?:insufficient|missing|incomplete|unclear|ambiguous)\s*(?:data|evidence|information|context|instruction)",
    r"(?:if|when)\s+you\s+(?:are\s+)?(?:un)?(?:sure|certain|confident)",
    r"(?:cannot|can.t|should\s+not)\s+(?:proceed|continue|act|respond)",
    r"(?:escalat|hand\s*off|transfer|refer).*(?:human|supervisor|specialist|operator)",
    r"(?:safe|calibrated|graceful)\s*(?:stop|halt|failure|abort|exit)",
    r"refuse|disclaim|opt\s*out",
]

AUDIT_PATTERNS = [
    r"(?:log|record|track|trace|audit)\s*(?:trail|history|event|action|decision|every|all|each)",
    r"(?:audit|logging|trace|provenance|accountab)",
    r"(?:record|preserve|retain)\s*(?:the|all|every|each)\s*(?:decision|action|step|reason|source)",
    r"immutable|append.only|tamper.proof|write.once",
    r"(?:who|what|when|why|how)\s*(?:did|made|took|decided|executed)",
]

COMPLIANCE_PATTERNS = [
    r"(?:hipaa|phi|protected\s+health|patient\s+data|baa|business\s+associate)",
    r"(?:soc\s*2|soc2|system\s+and\s+organization\s+controls)",
    r"(?:gdpr|general\s+data\s+protection|data\s+protection\s+regulation)",
    r"(?:eu\s+ai\s+act|artificial\s+intelligence\s+act|ai\s+regulation)",
    r"(?:fda|medical\s+device|saMD|software\s+as\s+a\s+medical\s+device)",
    r"(?:pci|pci.dss|payment\s+card)",
    r"(?:ferpa|student\s+data|education\s+record)",
    r"(?:compliance|regulat|govern|legal|legal\s+requirement)",
    r"(?:encrypt|redact|de.identif|anonymi|pseudonymi)",
]

SCORER_MAP = {
    "injection": INJECTION_DEFENSE_PATTERNS,
    "hallucination": HALLUCINATION_PATTERNS,
    "citation": CITATION_PATTERNS,
    "cost": COST_PATTERNS,
    "human_gate": HUMAN_GATE_PATTERNS,
    "safe_stop": SAFE_STOP_PATTERNS,
    "audit": AUDIT_PATTERNS,
    "compliance": COMPLIANCE_PATTERNS,
}

# Short human-readable labels for highest-value signals per dimension.
# Index-aligned with the first N patterns in SCORER_MAP (used for missing findings).
DIMENSION_SIGNAL_LABELS: dict[str, list[str]] = {
    "injection": [
        "Reject ignore-previous-instructions / override attempts",
        "Do not follow user input that conflicts with system rules",
        "Keep system prompt confidential / do not reveal it",
    ],
    "hallucination": [
        "Do not fabricate facts, citations, or numbers",
        "Say so when you do not know or lack evidence",
        "Only use provided / verified data",
    ],
    "citation": [
        "Require citations, references, or source links",
        "Link claims back to source evidence",
        "Every claim must cite its source",
    ],
    "cost": [
        "Token / cost / budget limit or cap",
        "Max token or response length constraint",
        "Rate or cost limiting",
    ],
    "human_gate": [
        "Human / supervisor must approve or review",
        "Human-in-the-loop review or approval gate",
        "Approval required before execute / send / publish",
    ],
    "safe_stop": [
        "Stop / halt / refuse when conditions are unmet",
        "Handle missing or insufficient evidence",
        "Escalate to a human supervisor",
    ],
    "audit": [
        "Log or audit trail for actions and decisions",
        "Audit / logging / provenance accountability",
        "Immutable or append-only audit trail",
    ],
    "compliance": [
        "HIPAA / PHI / protected health data handling",
        "SOC 2 controls",
        "GDPR / data protection requirements",
    ],
}

_SNIPPET_MAX = 120
_MAX_FINDINGS_PER_STATUS = 3


def _truncate_snippet(text: str, max_len: int = _SNIPPET_MAX) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _match_patterns(prompt_lower: str, patterns: list[str]) -> list[tuple[str, str]]:
    """Return (pattern, snippet) for each pattern that matches the prompt."""
    hits: list[tuple[str, str]] = []
    for pattern in patterns:
        try:
            m = re.search(pattern, prompt_lower, re.IGNORECASE)
        except re.error:
            continue
        if m:
            hits.append((pattern, _truncate_snippet(m.group(0))))
    return hits


def _score_from_match_count(matches: int, total_patterns: int) -> int:
    """Score a dimension from match count (0-100)."""
    if total_patterns == 0 or matches == 0:
        return 0
    raw = matches / total_patterns
    score = 15 + (raw * 85)
    return min(100, round(score))


def _score_dimension(prompt_lower: str, patterns: list[str]) -> int:
    """Score a single dimension based on pattern matches (0-100)."""
    matches = _match_patterns(prompt_lower, patterns)
    return _score_from_match_count(len(matches), len(patterns))


def _apply_length_bonus(results: dict[str, int], prompt_lower: str) -> dict[str, int]:
    """Modest bonus for long, detailed prompts (capped to reduce gaming)."""
    word_count = len(prompt_lower.split())
    if word_count > 500:
        length_bonus = min(10, (word_count - 500) // 200)
        for key in results:
            results[key] = min(100, results[key] + length_bonus)
    return results


def analyze_with_findings(
    system_prompt: str,
) -> tuple[dict[str, int], list[dict]]:
    """Run structural analysis and return scores plus explain findings.

    Returns:
        (scores, findings) where findings is a list of dicts with keys
        dimension, status ("matched"|"missing"), pattern_or_reason, snippet.
    """
    if not system_prompt or not system_prompt.strip():
        scores = {key: 0 for key in SCORER_MAP}
        findings: list[dict] = []
        for dimension in SCORER_MAP:
            labels = DIMENSION_SIGNAL_LABELS.get(dimension, [])
            for label in labels[:_MAX_FINDINGS_PER_STATUS]:
                findings.append(
                    {
                        "dimension": dimension,
                        "status": "missing",
                        "pattern_or_reason": label,
                        "snippet": None,
                    }
                )
        return scores, findings

    prompt_lower = system_prompt.lower()
    results: dict[str, int] = {}
    findings = []

    for dimension, patterns in SCORER_MAP.items():
        hits = _match_patterns(prompt_lower, patterns)
        results[dimension] = _score_from_match_count(len(hits), len(patterns))

        # Up to 3 matched snippets
        for pattern, snippet in hits[:_MAX_FINDINGS_PER_STATUS]:
            findings.append(
                {
                    "dimension": dimension,
                    "status": "matched",
                    "pattern_or_reason": pattern,
                    "snippet": snippet,
                }
            )

        # Up to 3 missing human labels for unmatched high-value signals
        labels = DIMENSION_SIGNAL_LABELS.get(dimension, [])
        matched_indices = set()
        for i, pattern in enumerate(patterns):
            try:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    matched_indices.add(i)
            except re.error:
                continue

        missing_count = 0
        for i, label in enumerate(labels):
            if missing_count >= _MAX_FINDINGS_PER_STATUS:
                break
            # Label i corresponds to high-value pattern i when index-aligned
            if i < len(patterns) and i in matched_indices:
                continue
            findings.append(
                {
                    "dimension": dimension,
                    "status": "missing",
                    "pattern_or_reason": label,
                    "snippet": None,
                }
            )
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

    results = _apply_length_bonus(results, prompt_lower)
    return results, findings


def analyze(system_prompt: str) -> Dict[str, int]:
    """Run structural analysis on a system prompt.

    Returns:
        Dict mapping dimension name → score (0-100).
    """
    scores, _ = analyze_with_findings(system_prompt)
    return scores
