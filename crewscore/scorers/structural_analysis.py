"""
Structural analysis of an AI agent's system prompt.

Runs entirely offline — no LLM calls, no API key, no cost.
Analyzes the system prompt text for guardrail patterns, safety
instructions, and governance guardrail signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict

from crewscore.scoring import RULESET_ID

# Re-export for callers / web export.
__all__ = [
    "RULESET_ID",
    "SCORER_MAP",
    "CONCEPTS",
    "CONCEPT_COUNT",
    "Concept",
    "RULE_LABELS",
    "PATTERN_RULE_IDS",
    "analyze",
    "analyze_with_findings",
]

# Maximum characters allowed between a trigger and its closer in a two-part
# rule. These were written `TRIGGER.*CLOSER`, which backtracks quadratically
# when the trigger repeats and the closer never appears - 90 KB of one
# repeated trigger took ~10s, and one rule took 31s at 160 KB. A bound removes
# that, and is also more precise: these rules mean "trigger and closer near
# each other", not "anywhere in the same line".
_GAP = r".{0,200}"

# Keywords and patterns that signal guardrail presence.
# Each entry is (rule_id, regex). rule_ids are stable across releases.
INJECTION_DEFENSE_PATTERNS: list[tuple[str, str]] = [
    ("injection.01", r"ignore\s+(previous|above|all)\s+(instructions|prompts)"),
    (
        "injection.02",
        r"do\s+not\s+(follow|obey|listen)\s+to\s+(user|input)" + _GAP + r"(system|instruction)",
    ),
    (
        "injection.03",
        r"system\s+prompt" + _GAP + r"(?:confidential|private|do\s+not\s+reveal)",
    ),
    ("injection.04", r"reject" + _GAP + r"(?:inject|override|manipulat)"),
    # 0.3.1: was bare `injection`, which matched "dependency injection" and
    # "SQL injection" in 19/100 real repo files. Require the prompt sense.
    (
        "injection.05",
        r"(?:prompt|instruction|indirect)\s+injection|jailbreak|"
        r"adversarial\s+(?:input|prompt|attack|user)",
    ),
    (
        "injection.06",
        r"do\s+not\s+reveal\s+(your|the|this)\s+(system|instructions|prompt)",
    ),
    (
        "injection.07",
        r"you\s+cannot\s+be\s+(instructed|told|asked)\s+to\s+(ignore|override)",
    ),
    # 0.2.0: the canonical modern phrasing had no rule at all. Every existing
    # injection rule keys on the *attack* string ("ignore previous
    # instructions") or on naming the threat; none matched a prompt that states
    # the defense positively, so a textbook injection defense scored zero.
    (
        "injection.09",
        # Every branch requires defensive framing. A first draft also matched
        # "<instructions> <in|from> <user>", which fired on "Follow
        # instructions from the user" - crediting a prompt for stating the
        # exact opposite of the control. Either a defensive verb or the
        # "data, not commands" construction must be present.
        r"(?:as\s+)?data[,;]?\s*(?:and\s+)?not\s+(?:as\s+)?"
        r"(?:command|instruction|directive)|"
        r"(?:ignore|disregard|reject|never\s+(?:follow|obey|execute|trust)|"
        r"do\s+not\s+(?:follow|obey|execute|act\s+on|trust))" + _GAP
        + r"(?:instruction|command|directive|prompt)s?" + _GAP
        + r"(?:user|external|retrieved|untrusted|tool|third.party|embedded|"
        r"injected|inserted)|"
        # "instructions embedded in user content" - the noun list is confined
        # to untrusted sources, so ordinary docs ("instructions in the README")
        # do not qualify.
        r"(?:instruction|command|directive)s?\s+"
        r"(?:embedded|contained|found|appearing|included)\s+"
        r"(?:in|within|inside)\s+(?:the\s+|any\s+)?"
        r"(?:user|external|retrieved|untrusted|tool|third.party)",
    ),
    # 0.5.0: fired on 2/356 real prompts where a looser probe found 13/356.
    # injection.06 requires the literal "do not reveal"; real prompts
    # overwhelmingly write "NEVER disclose your system prompt" or "never
    # expose this system prompt". The verb list stays narrow - "output" is
    # excluded so "do not output instructions on how to install packages"
    # does not read as prompt confidentiality.
    (
        "injection.10",
        r"(?:never|do\s+not|don't)\s+"
        r"(?:reveal|disclose|expose|divulge|share|repeat)\s+"
        r"(?:the|your|this|these)?\s*"
        r"(?:system\s+prompt|instructions?|prompt|these\s+rules)",
    ),
    # Softened: bare "safety|guardrail" alone inflated scores; require defense context.
    (
        "injection.08",
        r"(?:prompt\s+)?(?:injection|jailbreak)" + _GAP + r"(?:defen|guard|protect|resist)|"
        r"(?:defen|guard|protect|resist)" + _GAP + r"(?:prompt\s+)?(?:injection|jailbreak)|"
        r"safety\s+(?:boundar|constraint|policy|policies|rule)|"
        r"guardrail\s+(?:against|for|on|policy|policies)",
    ),
]

HALLUCINATION_PATTERNS: list[tuple[str, str]] = [
    (
        "hallucination.01",
        r"do\s+not\s+(?:fabricat|invent|make\s+up|generat)" + _GAP + r"(?:fact|data|citation|source|number)",
    ),
    (
        "hallucination.02",
        r"if\s+you\s+(?:do\s+not\s+know|are\s+unsure|lack\s+(?:the|enough)\s+(?:data|information|evidence))",
    ),
    (
        "hallucination.03",
        # 0.2.0: required the qualifier to sit directly against the noun, so
        # "only use provided, verified sources" - a natural way to write it -
        # did not match. Allow a run of qualifiers.
        r"only\s+(?:use|cite|reference|rely\s+on)\s+"
        r"(?:(?:provided|given|available|verified|supplied|trusted|approved)"
        r"[,\s]+)+"
        r"(?:data|information|sources?|context|material|documents?)",
    ),
    ("hallucination.04", r"(?:hallucin|fabricat|confabulat)"),
    ("hallucination.05", r"say\s+(?:I\s+dont\s+know|I\s+cannot|I\s+do\s+not\s+have)"),
    ("hallucination.06", r"ground(?:ed|ing)\s+in\s+(?:the|provided|given)"),
    ("hallucination.07", r"do\s+not\s+guess|never\s+guess|avoid\s+guess"),
    (
        "hallucination.08",
        r"recommend" + _GAP + r"(?:consult|doctor|professional|specialist|expert)",
    ),
]

CITATION_PATTERNS: list[tuple[str, str]] = [
    # 0.3.1: was `cite|citation|reference|attribute|...`. "reference" and
    # "attribute" are ordinary words in developer docs and fired on 48/100
    # real files. Require language that actually asks for attribution.
    (
        "citation.01",
        r"\bcitations?\b|\bcite\s+(?:the|its|each|every|all|your|sources?)|"
        r"source\s+link|\bfootnotes?\b",
    ),
    ("citation.02", r"(?:source|evidence|provenance)\s*(?:link|id|span|reference)"),
    (
        "citation.03",
        r"every\s+(?:claim|statement|answer|output)\s+must\s+(?:cite|reference|include)",
    ),
    (
        "citation.04",
        r"link\s+(?:to|back\s+to)\s+(?:the|its|each)\s+(?:source|evidence|document)",
    ),
    # 0.3.1: was `\[?\d+\]?.*(?:source|ref|cite)`, which matched any numbered
    # list line containing "refer"/"prefer" — 35/100 real files. Require a
    # bracketed citation marker.
    ("citation.05", r"\[\d+\]|\[source[:\s]|\[ref[:\s]"),
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
        r"do\s+not\s+(?:auto|automatic)" + _GAP + r"(?:execute|send|submit|approve|publish)",
    ),
    (
        "human_gate.05",
        r"(?:require|mandate)" + _GAP + r"(?:human|manual)\s*(?:approval|review|confirmation)",
    ),
    (
        "human_gate.06",
        r"(?:staff|clinician|doctor|nurse|analyst|officer)\s*(?:review|approve|sign)",
    ),
    # 0.5.0: the corpus harness measured this control firing on 2/356 real
    # prompts while a looser probe found 24/356. Inspection confirmed the
    # misses were real: production prompts say "ask permission before
    # dangerous actions" and "get user approval", neither of which matches
    # human_gate.01 (which needs an actor + modal) or .05 (which needs
    # "require/mandate"). The negative lookbehinds keep "do not ask
    # permission" - the opposite instruction - from scoring as the control.
    (
        "human_gate.07",
        r"(?<!do not )(?<!don't )(?<!never )(?:ask|request|obtain|get|seek)\s+"
        r"(?:for\s+)?(?:the\s+)?(?:user|human|explicit|written|prior)?\s*"
        r"(?:permission|approval|consent|confirmation)",
    ),
]

SAFE_STOP_PATTERNS: list[tuple[str, str]] = [
    ("safe_stop.01", r"(?:stop|halt|pause|refuse|decline|abort)" + _GAP + r"(?:if|when|unless)"),
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
        r"(?:escalat|hand\s*off|transfer|refer)" + _GAP + r"(?:human|supervisor|specialist|operator)",
    ),
    ("safe_stop.06", r"(?:safe|calibrated|graceful)\s*(?:stop|halt|failure|abort|exit)"),
    ("safe_stop.07", r"refuse|disclaim|opt\s*out"),
]

AUDIT_PATTERNS: list[tuple[str, str]] = [
    (
        "audit.01",
        r"(?:log|record|track|trace|audit)\s*(?:trail|history|event|action|decision|every|all|each)",
    ),
    # 0.3.1: was `audit|logging|trace|provenance|accountab`. Bare "logging"
    # and "trace" are everyday build-doc words and fired on 30/100 real files.
    (
        "audit.02",
        r"audit\s+(?:trail|log|record)|\bprovenance\b|\baccountab|"
        r"immutable\s+log|log\s+(?:every|all|each)\b",
    ),
    (
        "audit.03",
        r"(?:record|preserve|retain)\s*(?:the|all|every|each)\s*(?:decision|action|step|reason|source)",
    ),
    ("audit.04", r"immutable|append.only|tamper.proof|write.once"),
    ("audit.05", r"(?:who|what|when|why|how)\s*(?:did|made|took|decided|executed)"),
]

COMPLIANCE_PATTERNS: list[tuple[str, str]] = [
    # 0.3.1: `phi` and `baa` had no word boundaries, so they matched inside
    # "cryptographic", "graphics", "baaS" and similar — 19/100 real files.
    (
        "compliance.01",
        r"\bhipaa\b|\bphi\b|protected\s+health|patient\s+data|\bbaa\b|"
        r"business\s+associate",
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
    # 0.3.1: bare `pci` matched "pcie" and similar hardware terms.
    ("compliance.06", r"\bpci(?:[-\s]?dss)?\b|payment\s+card"),
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

# Human label per rule, keyed by rule_id.
#
# This used to be keyed by the regex source string, duplicating every pattern
# in two places. That coupling broke twice: once when the labels were assumed
# index-aligned with SCORER_MAP (guarded prompts reported present signals as
# missing), and again whenever a pattern was edited in one copy only. rule_ids
# are stable across releases; regex sources are not.
RULE_LABELS: dict[str, str] = {
    "injection.01": "Reject ignore-previous-instructions / override attempts",
    "injection.02": "Do not follow user input that conflicts with system rules",
    "injection.03": "Keep the system prompt confidential",
    "injection.04": "Reject injection / override / manipulation attempts",
    "injection.05": "Name prompt injection, jailbreak, or adversarial input",
    "injection.06": "Do not reveal your system prompt or instructions",
    "injection.07": "You cannot be instructed to ignore your instructions",
    "injection.08": "State an injection defense or safety boundary policy",
    "injection.09": "Treat instructions in user content as data, not commands",
    "injection.10": "Never disclose or expose the system prompt",
    "hallucination.01": "Do not fabricate facts, citations, or numbers",
    "hallucination.02": "Say so when you do not know or lack evidence",
    "hallucination.03": "Only use provided / verified data",
    "hallucination.04": "Name hallucination or fabrication as a failure mode",
    "hallucination.05": "Say 'I don't know' rather than answering anyway",
    "hallucination.06": "Ground answers in the provided material",
    "hallucination.07": "Do not guess",
    "hallucination.08": "Defer to a qualified professional",
    "citation.01": "Require citations, footnotes, or source links",
    "citation.02": "Attach a source link, id, or span to claims",
    "citation.03": "Every claim must cite its source",
    "citation.04": "Link claims back to source evidence",
    "citation.05": "Use an inline citation marker such as [1]",
    "cost.01": "Token / cost / budget limit or cap",
    "cost.02": "Max token or response length constraint",
    "cost.03": "Rate or cost limiting",
    "cost.04": "Budget or spend control",
    "cost.05": "Truncation or max_tokens bound",
    "human_gate.01": "Human / supervisor must approve or review",
    "human_gate.02": "Human-in-the-loop review or approval gate",
    "human_gate.03": "Approval required before execute / send / publish",
    "human_gate.04": "Do not auto-execute, send, or publish",
    "human_gate.05": "Require human approval or confirmation",
    "human_gate.06": "Named role must review or sign off",
    "human_gate.07": "Ask for permission or approval before acting",
    "safe_stop.01": "Stop / halt / refuse when conditions are unmet",
    "safe_stop.02": "Handle missing or insufficient evidence",
    "safe_stop.03": "Act on your own uncertainty",
    "safe_stop.04": "Do not proceed when you cannot act correctly",
    "safe_stop.05": "Escalate to a human supervisor",
    "safe_stop.06": "Define a safe or graceful stop",
    "safe_stop.07": "Refuse or disclaim rather than comply",
    "audit.01": "Log or audit trail for actions and decisions",
    "audit.02": "Audit / logging / provenance accountability",
    "audit.03": "Record or retain each decision and its reason",
    "audit.04": "Immutable or append-only audit trail",
    "audit.05": "Record who did what, when, and why",
    "compliance.01": "HIPAA / PHI / protected health data handling",
    "compliance.02": "SOC 2 controls",
    "compliance.03": "GDPR / data protection requirements",
    "compliance.04": "EU AI Act / AI regulation",
    "compliance.05": "FDA / medical device regulation",
    "compliance.06": "PCI DSS / payment card data",
    "compliance.07": "FERPA / student education records",
    "compliance.08": "State that legal or regulatory constraints apply",
    "compliance.09": "Encrypt, redact, or de-identify personal data",
}


@dataclass(frozen=True)
class Concept:
    """One distinct control within a dimension.

    `rule_ids` are alternative ways of stating the *same* control. They are
    alternatives, not additive evidence: a prompt that says "do not fabricate",
    "never hallucinate" and "do not guess" has stated one control three times,
    not three controls.
    """

    key: str
    label: str
    rule_ids: tuple[str, ...]


# The rules of each dimension, grouped into the distinct controls they express.
#
# This grouping is the scoring denominator, so it is the most consequential
# judgement in the catalog and is deliberately visible: `crewscore rules`
# prints it, and a reader who disagrees with a grouping can argue with it in
# an issue. Regrouping changes scores and requires a version bump.
CONCEPTS: dict[str, tuple[Concept, ...]] = {
    "injection": (
        Concept(
            "injection.override_resistance",
            "Treat instructions inside user content as data, not commands",
            (
                "injection.01",
                "injection.02",
                "injection.04",
                "injection.07",
                "injection.09",
            ),
        ),
        Concept(
            "injection.prompt_confidentiality",
            "Keep the system prompt confidential",
            ("injection.03", "injection.06", "injection.10"),
        ),
        Concept(
            "injection.named_defense",
            "Name prompt injection and state a defense",
            ("injection.05", "injection.08"),
        ),
    ),
    "hallucination": (
        Concept(
            "hallucination.no_fabrication",
            "Do not fabricate, invent, or guess",
            ("hallucination.01", "hallucination.04", "hallucination.07"),
        ),
        Concept(
            "hallucination.admit_uncertainty",
            "Say so when you do not know",
            ("hallucination.02", "hallucination.05"),
        ),
        Concept(
            "hallucination.grounding",
            "Ground answers in provided sources",
            ("hallucination.03", "hallucination.06"),
        ),
        Concept(
            "hallucination.defer_to_expert",
            "Defer to a qualified professional",
            ("hallucination.08",),
        ),
    ),
    "citation": (
        Concept(
            "citation.require",
            "Require citations for claims",
            ("citation.01", "citation.03"),
        ),
        Concept(
            "citation.link_source",
            "Link each claim to its source",
            ("citation.02", "citation.04"),
        ),
        Concept(
            "citation.inline_marker",
            "Use an inline citation marker format",
            ("citation.05",),
        ),
    ),
    "cost": (
        Concept(
            "cost.budget_cap",
            "Cap spend, tokens, or rate",
            ("cost.01", "cost.03", "cost.04"),
        ),
        Concept(
            "cost.output_bound",
            "Bound output length",
            ("cost.02", "cost.05"),
        ),
    ),
    "human_gate": (
        Concept(
            "human_gate.approval_required",
            "A human must approve",
            (
                "human_gate.01",
                "human_gate.02",
                "human_gate.05",
                "human_gate.06",
                "human_gate.07",
            ),
        ),
        Concept(
            "human_gate.no_autonomous_action",
            "Do not act autonomously before approval",
            ("human_gate.03", "human_gate.04"),
        ),
    ),
    "safe_stop": (
        Concept(
            "safe_stop.stop_condition",
            "Stop or refuse rather than proceed",
            (
                "safe_stop.01",
                "safe_stop.04",
                "safe_stop.06",
                "safe_stop.07",
            ),
        ),
        Concept(
            "safe_stop.uncertainty_trigger",
            "Name what triggers stopping",
            ("safe_stop.02", "safe_stop.03"),
        ),
        Concept(
            "safe_stop.escalate",
            "Escalate to a human",
            ("safe_stop.05",),
        ),
    ),
    "audit": (
        Concept(
            "audit.log_actions",
            "Log actions and decisions",
            ("audit.01", "audit.02", "audit.03"),
        ),
        Concept(
            "audit.tamper_evident",
            "Keep the log tamper-evident",
            ("audit.04",),
        ),
        Concept(
            "audit.actor_attribution",
            "Record who did what and when",
            ("audit.05",),
        ),
    ),
    "compliance": (
        Concept(
            "compliance.named_regime",
            "Name the regime that applies",
            (
                "compliance.01",
                "compliance.02",
                "compliance.03",
                "compliance.04",
                "compliance.05",
                "compliance.06",
                "compliance.07",
            ),
        ),
        Concept(
            "compliance.stated_obligation",
            "State that legal or regulatory constraints apply",
            ("compliance.08",),
        ),
        Concept(
            "compliance.data_protection",
            "State a data-protection technique",
            ("compliance.09",),
        ),
    ),
}

CONCEPT_COUNT = sum(len(c) for c in CONCEPTS.values())

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


def covered_concepts(dimension: str, matched_rule_ids: set[str]) -> list[Concept]:
    """Concepts in `dimension` with at least one of their rules matched."""
    return [
        concept
        for concept in CONCEPTS.get(dimension, ())
        if any(rule_id in matched_rule_ids for rule_id in concept.rule_ids)
    ]


def score_from_concepts(covered: int, total: int) -> int:
    """The whole dimension formula: what fraction of controls are covered.

    Deliberately has no floor term and no length term. The previous formula
    opened at 15 for any single match, which made "said something vaguely
    related" and "stated one of three controls" indistinguishable.
    """
    if total == 0 or covered == 0:
        return 0
    # Integer round-half-up, not round(). Python's round() is half-to-even and
    # JavaScript's Math.round is half-up, so a dimension with 8 controls would
    # score 12 in the CLI and 13 in the browser off one covered control. Same
    # prompt, two numbers, is the one failure this project cannot ship.
    return (100 * covered + total // 2) // total


def _score_dimension(prompt_lower: str, dimension: str) -> int:
    """Score a single dimension by control coverage (0-100)."""
    hits = _match_patterns(prompt_lower, SCORER_MAP[dimension])
    matched = {rule_id for rule_id, _, _ in hits}
    return score_from_concepts(
        len(covered_concepts(dimension, matched)), len(CONCEPTS.get(dimension, ()))
    )


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


def _missing_finding(dimension: str, concept: Concept) -> dict:
    entry: dict = {
        "dimension": dimension,
        "status": "missing",
        "pattern_or_reason": concept.label,
        "snippet": None,
        "concept": concept.key,
    }
    if concept.rule_ids:
        # The canonical rule for this control, so a reader can go look it up.
        entry["rule_id"] = concept.rule_ids[0]
    return entry


def analyze_with_findings(
    system_prompt: str,
) -> tuple[dict[str, int], list[dict]]:
    """Run structural analysis and return scores plus explain findings.

    Findings are reported per *control*, not per regex. Listing every rule that
    fired would tell a reader who stated one control three ways that they have
    three things, which is the same double-count the score itself used to make.

    Returns:
        (scores, findings) where findings is a list of dicts with keys
        dimension, status ("matched"|"missing"), pattern_or_reason, snippet,
        concept, and rule_id.
    """
    findings: list[dict] = []

    if not system_prompt or not system_prompt.strip():
        scores = {key: 0 for key in SCORER_MAP}
        for dimension, concepts in CONCEPTS.items():
            findings.extend(_missing_finding(dimension, c) for c in concepts)
        return scores, findings

    prompt_lower = system_prompt.lower()
    results: dict[str, int] = {}

    for dimension, patterns in SCORER_MAP.items():
        hits = _match_patterns(prompt_lower, patterns)
        matched_ids = {rule_id for rule_id, _, _ in hits}
        snippet_for = {rule_id: snippet for rule_id, _, snippet in hits}

        concepts = CONCEPTS.get(dimension, ())
        covered = covered_concepts(dimension, matched_ids)
        results[dimension] = score_from_concepts(len(covered), len(concepts))

        covered_keys = {c.key for c in covered}
        for concept in covered:
            fired = next(r for r in concept.rule_ids if r in matched_ids)
            findings.append(
                {
                    "dimension": dimension,
                    "status": "matched",
                    "pattern_or_reason": concept.label,
                    "snippet": snippet_for[fired],
                    "rule_id": fired,
                    "concept": concept.key,
                }
            )
        findings.extend(
            _missing_finding(dimension, c)
            for c in concepts
            if c.key not in covered_keys
        )

    return results, findings


def analyze(system_prompt: str) -> Dict[str, int]:
    """Run structural analysis on a system prompt.

    Returns:
        Dict mapping dimension name → score (0-100).
    """
    scores, _ = analyze_with_findings(system_prompt)
    return scores
