"""Shared scoring result model and tier helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RULESET_ID = "crewscore-hygiene@0.5.0"

DIMENSIONS: list[tuple[str, str]] = [
    ("Prompt Injection Resistance", "injection"),
    ("Hallucination Guardrails", "hallucination"),
    ("Source Citation Requirements", "citation"),
    ("Cost Runaway Protection", "cost"),
    ("Human-in-the-Loop Gates", "human_gate"),
    ("Safe-Stop Behavior", "safe_stop"),
    ("Audit Trail & Provenance", "audit"),
    ("Compliance Readiness", "compliance"),
]

DIMENSION_KEYS = [key for _, key in DIMENSIONS]


@dataclass(frozen=True)
class ScoreResult:
    """Normalized structural scorecard for an agent prompt."""

    dimensions: dict[str, int]
    overall: int
    tier: str
    mode: str = "structural"
    source: str = "prompt"
    ruleset: str = RULESET_ID
    warnings: list[str] = field(default_factory=list)
    # Advisory configuration smells (arXiv:2606.15828). Reported, never scored —
    # see crewscore/smells.py for why they stay out of the number.
    smells: list[dict[str, Any]] = field(default_factory=list)
    # Which ruleset this artifact should be judged by (crewscore/profiles.py).
    profile: str = "system_prompt"
    # False for coding-agent config, where the governance dimensions are a
    # category error. `overall`/`dimensions` are computed but never published
    # for that artifact — read `tier`. See to_dict().
    governance_applicable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serializable payload. Coding-agent config carries no governance grade.

        `overall` and the per-dimension scores are omitted entirely rather than
        zeroed: a caller running `jq -e '.overall >= 50'` must not find a number
        to fail on for an artifact that is not judged on one. This mirrors the
        browser engine, which has never emitted either field for config
        (`web_export.py::analyzeArtifact`). The fields stay on the dataclass so
        internal callers that need the raw arithmetic still have it.
        """
        payload = asdict(self)
        if not self.governance_applicable:
            payload.pop("overall", None)
            payload.pop("dimensions", None)
        return payload


def overall_score(dimensions: dict[str, int]) -> int:
    if not dimensions:
        return 0
    return sum(dimensions.values()) // len(dimensions)


def config_tier(smell_count: int) -> str:
    """Verdict for coding-agent config, expressed in smells rather than points.

    Deliberately not a 0-100 grade. Measured against the arXiv:2606.15828
    corpus, the governance score puts 100/100 real config files in the worst
    tier — a scale where the whole population fails carries no information.
    Smell counts are what that artifact can honestly be judged on.
    """
    if smell_count <= 0:
        return "CONFIG: NO SMELLS DETECTED"
    if smell_count == 1:
        return "CONFIG: 1 SMELL"
    return f"CONFIG: {smell_count} SMELLS"


def score_tier(overall: int) -> str:
    if overall >= 90:
        return "STRUCTURAL: STRONG"
    if overall >= 70:
        return "STRUCTURAL: OK WITH GAPS"
    if overall >= 50:
        return "STRUCTURAL: WEAK"
    return "STRUCTURAL: CRITICAL GAPS"


def tier_color(overall: int) -> str:
    if overall >= 90:
        return "green"
    if overall >= 70:
        return "yellow"
    if overall >= 50:
        return "dark_orange"
    return "red"


def detect_template_boilerplate(prompt_text: str | None) -> list[str]:
    """Return warnings when CrewScore fix templates dominate the prompt."""
    if not prompt_text:
        return []
    from crewscore.scorers.fix_patterns import FIX_TEMPLATES

    warnings: list[str] = []
    markers = [
        "CrewScore",
        "## Prompt Injection Defense",
        "# Guardrails (Applied by CrewScore)",
        "## Additional Guardrails (Applied by CrewScore)",
    ]
    # Section headers from each fix template (first non-empty line).
    for template in FIX_TEMPLATES.values():
        for line in template.strip().splitlines():
            line = line.strip()
            if line.startswith("## "):
                markers.append(line)
                break

    hits = sum(1 for m in markers if m in prompt_text)
    # Two or more template markers (or the explicit CrewScore apply header) → warn.
    if "CrewScore" in prompt_text and hits >= 2:
        warnings.append("template_boilerplate_detected")
    elif hits >= 3:
        warnings.append("template_boilerplate_detected")
    return warnings


def build_result(
    dimensions: dict[str, int],
    *,
    mode: str = "structural",
    source: str = "prompt",
    prompt_text: str | None = None,
    warnings: list[str] | None = None,
    smells: list[dict[str, Any]] | None = None,
    profile: str | None = None,
) -> ScoreResult:
    from crewscore.profiles import SYSTEM_PROMPT, governance_applies

    resolved_profile = profile or SYSTEM_PROMPT
    resolved_smells = list(smells) if smells else []
    applicable = governance_applies(resolved_profile)

    overall = overall_score(dimensions)
    resolved_warnings = list(warnings) if warnings is not None else []
    if warnings is None and prompt_text is not None:
        resolved_warnings = detect_template_boilerplate(prompt_text)
    return ScoreResult(
        dimensions=dimensions,
        overall=overall,
        tier=score_tier(overall)
        if applicable
        else config_tier(len(resolved_smells)),
        mode=mode,
        source=source,
        ruleset=RULESET_ID,
        warnings=resolved_warnings,
        smells=resolved_smells,
        profile=resolved_profile,
        governance_applicable=applicable,
    )
