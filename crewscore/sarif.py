"""Prompt-free SARIF export for missing written controls.

The report deliberately contains control IDs and file locations only.  It does
not copy prompt snippets into a CI artifact or GitHub code-scanning record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewscore.scorers.structural_analysis import CONCEPTS


SARIF_VERSION = "2.1.0"
_HELP_BASE = "https://github.com/shmindmaster/crewscore/blob/main/docs/scoring.md"


def _rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for dimension, concepts in CONCEPTS.items():
        for concept in concepts:
            rules.append(
                {
                    "id": f"crewscore.{concept.key}",
                    "name": concept.key,
                    "shortDescription": {"text": concept.label},
                    "fullDescription": {
                        "text": (
                            "CrewScore did not detect this published written control. "
                            "This is coverage evidence, not a runtime safety verdict."
                        )
                    },
                    "helpUri": _HELP_BASE,
                    "properties": {
                        "dimension": dimension,
                        "control": concept.key,
                        "kind": "written-control-coverage",
                    },
                }
            )
    return rules


def render_sarif(
    entries: list[tuple[str, bool, list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Render SARIF from ``(source, applicable, findings)`` entries."""
    results: list[dict[str, Any]] = []
    for source, applicable, findings in entries:
        if not applicable:
            continue
        uri = source.replace("\\", "/")
        for finding in findings:
            if finding.get("status") != "missing" or not finding.get("concept"):
                continue
            control = finding["concept"]
            result: dict[str, Any] = {
                "ruleId": f"crewscore.{control}",
                "level": "warning",
                "message": {
                    "text": (
                        f"Written control not detected: {finding.get('pattern_or_reason') or control}. "
                        "Review the prompt and runtime enforcement; this is not a safety grade."
                    )
                },
                "properties": {"control": control, "dimension": finding.get("dimension")},
            }
            if source != "prompt":
                result["locations"] = [
                    {"physicalLocation": {"artifactLocation": {"uri": uri}}}
                ]
            results.append(result)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CrewScore",
                        "informationUri": "https://crewscore.ai",
                        "rules": _rules(),
                    }
                },
                "results": results,
            }
        ],
    }


def write_sarif(path: str | Path, entries: list[tuple[str, bool, list[dict[str, Any]]]]) -> None:
    import json

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(render_sarif(entries), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
