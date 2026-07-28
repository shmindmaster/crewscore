"""Shared scoring result model and tier helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RULESET_ID = "crewscore-hygiene@0.2.2"

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def overall_score(dimensions: dict[str, int]) -> int:
    if not dimensions:
        return 0
    return sum(dimensions.values()) // len(dimensions)


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
) -> ScoreResult:
    overall = overall_score(dimensions)
    resolved_warnings = list(warnings) if warnings is not None else []
    if warnings is None and prompt_text is not None:
        resolved_warnings = detect_template_boilerplate(prompt_text)
    return ScoreResult(
        dimensions=dimensions,
        overall=overall,
        tier=score_tier(overall),
        mode=mode,
        source=source,
        ruleset=RULESET_ID,
        warnings=resolved_warnings,
    )
