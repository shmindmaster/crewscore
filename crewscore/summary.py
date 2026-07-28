"""Transparent markdown summaries for CI / PR comments (not a black box)."""

from __future__ import annotations

from typing import Any

from crewscore.scoring import DIMENSIONS, RULESET_ID, ScoreResult

# Plain-language explanation for warning keys that a reader cannot act on
# from the key alone.
_WARNING_NOTES = {
    "template_boilerplate_detected": (
        "Score may be inflated by pasted fix templates "
        "(text coverage ≠ runtime safety)."
    ),
    "threshold_ignored_for_config": (
        "`--threshold` gates the governance score, which this artifact is not "
        "judged on — the gate did nothing. Use `--max-smells N` to gate CI here."
    ),
}


def _warning_lines(warnings: list[str]) -> list[str]:
    """Markdown for a result's warnings; empty when there are none."""
    if not warnings:
        return []
    lines = ["", "### Warnings"]
    for w in warnings:
        lines.append(f"- ⚠️ `{w}`")
        note = _WARNING_NOTES.get(w)
        if note:
            lines.append(f"  - {note}")
    return lines


def format_score_markdown(
    result: ScoreResult | dict[str, Any],
    *,
    findings: list[dict[str, Any]] | None = None,
    title: str = "CrewScore structural hygiene",
    max_findings: int = 24,
) -> str:
    """GitHub-flavored markdown: score, formula, open rule findings."""
    if isinstance(result, ScoreResult):
        data = result.to_dict()
    else:
        data = dict(result)

    overall = int(data.get("overall", 0))
    tier = str(data.get("tier", ""))
    ruleset = str(data.get("ruleset") or RULESET_ID)
    dims = data.get("dimensions") or {}
    warnings = data.get("warnings") or []
    source = data.get("source") or "prompt"
    governed = data.get("governance_applicable", True)
    smells = data.get("smells") or []

    if not governed:
        # Coding-agent config: report smells, never a governance grade. A
        # PR comment saying "0/100 CRITICAL GAPS" on a build-instructions
        # file is wrong and would be the first thing a reviewer mocks.
        lines = [
            f"## {title}",
            "",
            f"**`{tier}`** — coding-agent config",
            "",
            f"- **Ruleset:** `{ruleset}` (deterministic · no LLM)",
            f"- **Source:** `{source}`",
            "- **Judged on:** configuration smells "
            "([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)), "
            "not the production-governance dimensions",
            "- **Not:** red-team, runtime proof, or certification",
        ]
        if smells:
            lines.extend(["", "| Smell | Detail |", "| --- | --- |"])
            for s in smells:
                detail = str(s.get("detail", "")).replace("|", "\\|")
                lines.append(f"| **{s.get('name', '?')}** | {detail} |")
        else:
            lines.extend(["", "No configuration smells detected."])
        # Warnings matter most here: the Action always passes --threshold, so
        # this comment is the only place a CI owner learns their gate was a
        # no-op on this file.
        lines.extend(_warning_lines(warnings))
        return "\n".join(lines) + "\n"

    lines = [
        f"## {title}",
        "",
        f"**{overall}/100** — `{tier}`",
        "",
        f"- **Ruleset:** `{ruleset}` (deterministic regex · no LLM)",
        f"- **Source:** `{source}`",
        "- **Formula:** dim = `min(100, round(15+85×matches/rules))`; overall = mean of 8 dims",
        "- **Open rules:** `crewscore rules --json`",
        "- **Not:** red-team, runtime proof, or certification",
        "",
        "| Dimension | Score |",
        "| --- | ---: |",
    ]
    for label, key in DIMENSIONS:
        score = int(dims.get(key, 0))
        lines.append(f"| {label} | {score} |")

    lines.extend(_warning_lines(warnings))

    if findings:
        lines.extend(["", "### Findings (open rule IDs)", ""])
        shown = 0
        by_dim: dict[str, list[dict]] = {}
        for f in findings:
            by_dim.setdefault(str(f.get("dimension", "?")), []).append(f)
        for label, key in DIMENSIONS:
            items = by_dim.get(key, [])
            if not items:
                continue
            lines.append(f"**{label}** (`{key}`)")
            for f in items:
                if shown >= max_findings:
                    lines.append("")
                    lines.append(f"_…truncated after {max_findings} findings_")
                    return "\n".join(lines) + "\n"
                status = f.get("status") or "?"
                rid = f.get("rule_id")
                rid_s = f"`{rid}` " if rid else ""
                detail = f.get("snippet") or f.get("pattern_or_reason") or ""
                icon = "✅" if status == "matched" else "❌"
                lines.append(f"- {icon} **{status}** {rid_s}{detail}")
                shown += 1
            lines.append("")

    lines.extend(
        [
            "",
            "---",
            "_Structural pre-gate only. Next: [Promptfoo](https://www.promptfoo.dev/) "
            "/ [garak](https://github.com/NVIDIA/garak). "
            "See `docs/next-steps-eval.md`._",
            "",
        ]
    )
    return "\n".join(lines)


def format_scan_markdown(
    results: list[dict[str, Any]],
    *,
    title: str = "CrewScore scan (repo)",
) -> str:
    """Markdown table for multi-file scan results.

    Coding-agent config never contributes a governance grade: it cannot be the
    headline score, and its row shows the smell verdict instead of a number.
    This body is the sticky PR comment and the job summary, so a config file
    displacing the real prompt at 0/100 would be the most visible defect there is.
    """
    if not results:
        return f"## {title}\n\n_No agent prompt files found._\n"

    governed = [r for r in results if r.get("governance_applicable", True)]
    config = [r for r in results if not r.get("governance_applicable", True)]
    ruleset = (governed or results)[0].get("ruleset") or RULESET_ID

    lines = [f"## {title}", ""]
    if governed:
        worst = min(governed, key=lambda r: int(r.get("overall", 0)))
        lines.append(
            f"**Worst score:** **{worst.get('overall', 0)}/100** "
            f"(`{worst.get('tier', '')}`) on `{worst.get('path', '?')}`"
        )
    else:
        # Nothing here is judged on the governance dimensions, so there is no
        # score to headline — say that rather than inventing a zero.
        lines.append(
            f"**No governance grade:** all {len(config)} file(s) scanned are "
            "coding-agent config, judged on configuration smells."
        )
    lines.extend(
        [
            "",
            f"- **Ruleset:** `{ruleset}` · open rules: `crewscore rules --json`",
        ]
    )
    if config:
        lines.append(
            f"- **Coding-agent config ({len(config)}):** judged on configuration "
            "smells ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)), "
            "not the production-governance dimensions"
        )
    lines.extend(
        [
            "- Not a red-team / not runtime proof",
            "",
            "| Path | Score | Tier |",
            "| --- | ---: | --- |",
        ]
    )
    for r in sorted(results, key=lambda x: str(x.get("path", ""))):
        score = (
            r.get("overall", 0)
            if r.get("governance_applicable", True)
            else "n/a"
        )
        lines.append(
            f"| `{r.get('path', '')}` | {score} | `{r.get('tier', '')}` |"
        )
    lines.extend(["", "---", "_Structural pre-gate only._", ""])
    return "\n".join(lines)
