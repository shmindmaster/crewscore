"""
AI Vendor Checklist — summarize self-attested diligence responses.

Non-technical. No API key. It is neither an independent audit nor a vendor
verdict.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

console = Console()
err_console = Console(stderr=True)

HOMEPAGE = "https://crewscore.ai"
REPO = "https://github.com/shmindmaster/crewscore"

# Bump when the JSON answer shape changes in a breaking way.
VENDOR_SCHEMA_VERSION = "1.1"

QUESTIONS = [
    ("Can you demo it with YOUR data, not their cherry-picked showcase?", "vapor_demo"),
    ("Published accuracy/reliability benchmark from an independent third party?", "benchmark"),
    ("SOC2 / HIPAA / ISO 27001 certified (not 'in progress' or 'compliant-ready')?", "certification"),
    ("Full audit trail: you can see what the AI did and why?", "audit"),
    ("Documented human-override path for critical decisions?", "human_override"),
    ("You can export your data if you leave (no vendor lock-in)?", "portability"),
    ("Pricing is transparent and predictable (no surprise token costs)?", "pricing"),
    ("Published security audit or pen test within the last 12 months?", "security_audit"),
    ("Can show 3+ customers in YOUR industry running in production (not pilots)?", "production_refs"),
    ("Documented incident/escalation process when the AI fails?", "incident"),
]

# Map checklist keys to related CrewScore written-control themes.
# These are follow-up suggestions for the buyer's own agent prompts / CI —
# never a claim that the vendor implements those controls.
QUESTION_CREWSCORE_THEMES: dict[str, dict[str, Any]] = {
    "vapor_demo": {
        "dimensions": [],
        "controls": [],
        "why": "Ask for a demo on your data; CrewScore cannot validate vendor demos.",
    },
    "benchmark": {
        "dimensions": ["hallucination", "citation"],
        "controls": ["hallucination.no_fabrication", "citation.require"],
        "why": "Independent benchmarks are evidence; written hallucination/citation controls are a separate prompt hygiene check.",
    },
    "certification": {
        "dimensions": ["compliance"],
        "controls": ["compliance.named_regime"],
        "why": "Certification is evidence of process; naming a regulation in a prompt is not certification.",
    },
    "audit": {
        "dimensions": ["audit"],
        "controls": ["audit.log_actions", "audit.tamper_evident"],
        "why": "Request vendor audit-trail evidence; also check your own agent prompts for written audit language.",
    },
    "human_override": {
        "dimensions": ["human_gate", "safe_stop"],
        "controls": ["human_gate.approval_required", "safe_stop.stop_condition"],
        "why": "Vendor override path is operational; your agent text should still state human gates and stop conditions.",
    },
    "portability": {
        "dimensions": [],
        "controls": [],
        "why": "Data export is a contract/ops issue, not a CrewScore control.",
    },
    "pricing": {
        "dimensions": ["cost"],
        "controls": ["cost.budget_cap"],
        "why": "Transparent pricing is commercial; written cost limits in agent prompts are a separate control.",
    },
    "security_audit": {
        "dimensions": ["injection", "compliance"],
        "controls": ["injection.override_resistance", "compliance.named_regime"],
        "why": "Pen tests are runtime evidence; pair with injection and compliance wording checks on your side.",
    },
    "production_refs": {
        "dimensions": [],
        "controls": [],
        "why": "Customer references are diligence evidence, not a written-control score.",
    },
    "incident": {
        "dimensions": ["safe_stop", "human_gate", "audit"],
        "controls": [
            "safe_stop.stop_condition",
            "human_gate.approval_required",
            "audit.log_actions",
        ],
        "why": "Incident process is operational; written stop/escalation/audit language still belongs in agent prompts.",
    },
}

# Critical diligence keys: NO or DK → explicit red-flag bullets
CRITICAL_KEYS = frozenset(
    {
        "certification",
        "audit",
        "human_override",
        "security_audit",
        "incident",
    }
)

SCORE_YES = 10
SCORE_DK = 3
SCORE_NO = 0

TIERS = [
    (80, "MOSTLY POSITIVE RESPONSES", "green", "Collect independent evidence"),
    (50, "FOLLOW-UP NEEDED", "yellow", "Review the unanswered and negative responses"),
    (30, "MATERIAL GAPS", "dark_orange", "Request evidence before relying on it"),
    (0, "INSUFFICIENT EVIDENCE", "red", "Do not treat this as a vendor verdict"),
]


def get_tier(score: int) -> tuple[str, str, str]:
    for threshold, name, color, label in TIERS:
        if score >= threshold:
            return name, color, label
    return "INSUFFICIENT EVIDENCE", "red", "Do not treat this as a vendor verdict"


def render_answer(ans: str) -> tuple[int, str]:
    normalized = ans.lower().strip()
    if normalized in ("y", "yes"):
        return SCORE_YES, "YES"
    if normalized in ("dk", "dont know", "don't know", "unsure"):
        return SCORE_DK, "DON'T KNOW"
    return SCORE_NO, "NO"


def _flag_label(question: str) -> str:
    return question.rstrip("?")


def collect_red_flags(results: list[tuple[str, str, int, str]]) -> list[str]:
    """Build red-flag bullets: all NOs, plus DK on critical keys."""
    flags: list[str] = []
    seen: set[str] = set()
    for question, label, pts, key in results:
        is_no = pts == SCORE_NO
        is_critical_dk = key in CRITICAL_KEYS and pts == SCORE_DK
        if is_no or is_critical_dk:
            text = _flag_label(question)
            if text not in seen:
                seen.add(text)
                flags.append(text)
    return flags


def _answer_records(
    results: list[tuple[str, str, int, str]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for q, label, pts, key in results:
        theme = QUESTION_CREWSCORE_THEMES.get(key, {})
        records.append(
            {
                "question": q,
                "key": key,
                "answer": label,
                "points": pts,
                "critical": key in CRITICAL_KEYS,
                "crewscore_dimensions": list(theme.get("dimensions") or []),
                "crewscore_controls": list(theme.get("controls") or []),
            }
        )
    return records


def next_crewscore_checks(results: list[tuple[str, str, int, str]]) -> list[dict[str, Any]]:
    """Suggest CrewScore follow-ups for gaps (NO or critical DK), without grading the vendor."""
    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for question, _label, pts, key in results:
        is_gap = pts == SCORE_NO or (key in CRITICAL_KEYS and pts == SCORE_DK)
        if not is_gap:
            continue
        theme = QUESTION_CREWSCORE_THEMES.get(key) or {}
        dims = list(theme.get("dimensions") or [])
        controls = list(theme.get("controls") or [])
        if not dims and not controls:
            continue
        dedupe = key
        if dedupe in seen:
            continue
        seen.add(dedupe)
        suggestions.append(
            {
                "from_question_key": key,
                "from_question": _flag_label(question),
                "dimensions": dims,
                "controls": controls,
                "why": theme.get("why", ""),
                "suggested_cli": (
                    "crewscore scan . --require "
                    + ",".join(controls[:2] if controls else dims)
                    if (controls or dims)
                    else "crewscore scan ."
                ),
            }
        )
    return suggestions


def build_vendor_result(name: str, answers_csv: str) -> dict:
    """Pure self-attested vendor checklist from comma-separated y/n/dk answers."""
    parts = [p.strip() for p in answers_csv.split(",")]
    if len(parts) != 10:
        raise ValueError(f"Expected 10 answers (y/n/dk), got {len(parts)}")

    results: list[tuple[str, str, int, str]] = []
    for (question, key), ans in zip(QUESTIONS, parts):
        pts, label = render_answer(ans)
        results.append((question, label, pts, key))

    total = sum(pts for _, _, pts, _ in results)
    tier_name, _tier_color, tier_label = get_tier(total)
    red_flags = collect_red_flags(results)
    answers = _answer_records(results)
    followups = next_crewscore_checks(results)

    return {
        "schema_version": VENDOR_SCHEMA_VERSION,
        "vendor": name,
        "score": total,
        "tier": tier_name,
        "tier_label": tier_label,
        "self_attested": True,
        "not_independent_audit": True,
        "not_vendor_safety_grade": True,
        "answers": answers,
        "red_flags": red_flags,
        "next_crewscore_checks": followups,
        "question_count": len(QUESTIONS),
    }


def build_vendor_result_from_rows(
    name: str, results: list[tuple[str, str, int, str]]
) -> dict:
    """Build the same payload from interactive (question, label, points, key) rows."""
    if len(results) != len(QUESTIONS):
        raise ValueError(f"Expected {len(QUESTIONS)} answers, got {len(results)}")
    total = sum(pts for _, _, pts, _ in results)
    tier_name, _tier_color, tier_label = get_tier(total)
    return {
        "schema_version": VENDOR_SCHEMA_VERSION,
        "vendor": name,
        "score": total,
        "tier": tier_name,
        "tier_label": tier_label,
        "self_attested": True,
        "not_independent_audit": True,
        "not_vendor_safety_grade": True,
        "answers": _answer_records(results),
        "red_flags": collect_red_flags(results),
        "next_crewscore_checks": next_crewscore_checks(results),
        "question_count": len(QUESTIONS),
    }


def render_vendor_html(payload: dict) -> str:
    """Simple self-contained HTML summary for a vendor checklist."""
    vendor = escape(str(payload.get("vendor", "")))
    score = payload.get("score", 0)
    tier = escape(str(payload.get("tier", "")))
    tier_label = escape(str(payload.get("tier_label", "")))
    red_flags = payload.get("red_flags") or []
    answers = payload.get("answers") or []
    followups = payload.get("next_crewscore_checks") or []

    flag_items = "".join(f"<li>{escape(f)}</li>" for f in red_flags)
    flags_block = (
        f'<div class="flags"><strong>Red flags</strong><ul>{flag_items}</ul></div>'
        if red_flags
        else ""
    )

    follow_items = []
    for item in followups:
        why = escape(str(item.get("why", "")))
        cli = escape(str(item.get("suggested_cli", "")))
        dims = ", ".join(escape(str(d)) for d in (item.get("dimensions") or []))
        follow_items.append(
            f"<li><strong>{escape(str(item.get('from_question', '')))}</strong>"
            f" — related CrewScore dimensions: {dims or 'n/a'}. {why}"
            f"<br><code>{cli}</code></li>"
        )
    follow_block = (
        f'<div class="followups"><strong>Suggested CrewScore follow-ups '
        f"(your prompts / CI, not a vendor grade)</strong>"
        f"<ul>{''.join(follow_items)}</ul></div>"
        if follow_items
        else ""
    )

    rows = []
    for a in answers:
        q = escape(str(a.get("question", "")))
        ans = escape(str(a.get("answer", "")))
        pts = a.get("points", 0)
        rows.append(f"<tr><td>{q}</td><td>{ans}</td><td>{pts}</td></tr>")
    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CrewScore — {vendor} Vendor Diligence Checklist</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f0f1a;color:#e2e8f0;padding:2rem;max-width:720px;margin:0 auto}}
h1{{color:#fff}}
.score{{font-size:2.5rem;font-weight:bold;margin:0.5rem 0}}
.tier{{color:#94a3b8;margin-bottom:1rem}}
table{{width:100%;border-collapse:collapse;font-size:0.85rem}}
td,th{{border:1px solid #334155;padding:0.5rem;text-align:left}}
.flags{{margin-top:1rem;color:#ef4444}}
.flags ul{{margin:0.5rem 0 0 1.25rem}}
.followups{{margin-top:1.25rem;color:#cbd5e1;font-size:0.9rem}}
.followups ul{{margin:0.5rem 0 0 1.25rem}}
.followups code{{font-size:0.8rem;color:#93c5fd}}
.disclaimer{{margin-top:1.5rem;font-size:0.8rem;color:#64748b}}
a{{color:#3b82f6}}
</style>
</head>
<body>
<h1>CrewScore — AI Vendor Diligence Checklist</h1>
<p>Vendor: <strong>{vendor}</strong></p>
<div class="score">Checklist response total: {score}/100</div>
<div class="tier">{tier} — {tier_label}</div>
{flags_block}
{follow_block}
<table>
<thead><tr><th>Question</th><th>Answer</th><th>Pts</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<p class="disclaimer">
Self-attested answers only — not an independent audit, certification, or vendor verdict.
Use the questions to request evidence; do not infer runtime behavior or production suitability.
<a href="{HOMEPAGE}">{HOMEPAGE}</a>
</p>
</body>
</html>
"""


def generate_linkedin_post(
    vendor: str,
    score: int,
    tier: str,
    answers: list[tuple[str, str, int]],
    red_flags: list[str] | None = None,
) -> str:
    if red_flags is None:
        red_flags = [q for q, ans, pts in answers if pts == SCORE_NO]
    cautions = [q for q, ans, pts in answers if pts == SCORE_DK]

    lines = [
        f"{vendor} completed a self-attested AI vendor diligence checklist.",
        "This is not an independent audit or a vendor verdict.",
        "",
        f"Checklist response total: {score}/100 -- {tier}",
        "",
    ]

    if red_flags:
        lines.append("Red flags:")
        for q in red_flags:
            lines.append(f"- {q.rstrip('?')}")
        lines.append("")

    if cautions:
        # Avoid double-listing critical DKs already in red_flags
        flag_set = {f.rstrip("?") for f in red_flags}
        remaining = [q for q in cautions if q.rstrip("?") not in flag_set]
        if remaining:
            lines.append("Couldn't verify:")
            for q in remaining:
                lines.append(f"- {q.rstrip('?')}")
            lines.append("")

    lines.append("Request evidence for each answer before making a vendor decision.")
    lines.append("")
    lines.append(f"Use the checklist: pip install crewscore && crewscore assess-vendor")
    lines.append(HOMEPAGE)
    lines.append("")
    lines.append("#AI #AIVendors #DueDiligence #EnterpriseAI #AIProcurement")

    return "\n".join(lines)


@click.command("assess-vendor")
@click.option("--name", "-n", required=True, help="Vendor/product name for the checklist")
@click.option(
    "--answers",
    "-a",
    help="Comma-separated answers (y/n/dk x10): 'y,y,n,dk,y,y,n,y,n,y'",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit machine-readable JSON",
)
@click.option(
    "--report",
    type=click.Path(),
    default=None,
    help="Write a self-attested HTML checklist summary to this path",
)
def assess_vendor(name: str, answers: str | None, as_json: bool, report: str | None):
    """Summarize a self-attested AI vendor checklist. 10 questions. No API key."""

    results: list[tuple[str, str, int, str]] = []

    if answers:
        parts = [p.strip() for p in answers.split(",")]
        if len(parts) != 10:
            err_console.print(
                f"[red]Error: Expected 10 answers (y/n/dk), got {len(parts)}[/red]"
            )
            err_console.print(
                "[dim]Example: crewscore assess-vendor --name 'Acme AI' "
                "--answers 'y,y,n,dk,y,y,n,y,n,y'[/dim]"
            )
            raise SystemExit(1)
        payload = build_vendor_result(name, answers)
        for a in payload["answers"]:
            results.append((a["question"], a["answer"], a["points"], a["key"]))
    elif as_json:
        err_console.print(
            "[red]Error: --json requires --answers (non-interactive).[/red]"
        )
        raise SystemExit(1)
    elif report is not None:
        err_console.print(
            "[red]Error: --report requires --answers (non-interactive).[/red]"
        )
        raise SystemExit(1)
    else:
        console.print()
        console.print(
            Panel(
                f"[bold]CREWSCORE — AI Vendor Diligence Checklist[/bold]\n"
                f"Vendor: [bold]{name}[/bold]\n"
                "[dim]Self-attested responses only; not an audit or verdict.[/dim]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        console.print(
            "[bold]Answer each question with y (yes), n (no), or dk (don't know)[/bold]"
        )
        console.print()
        for i, (question, key) in enumerate(QUESTIONS, 1):
            console.print(f"  {i}. {question}")
            ans = input("     [y/n/dk]: ").strip()
            pts, label = render_answer(ans)
            results.append((question, label, pts, key))
            console.print()

        payload = build_vendor_result_from_rows(name, results)

    total = payload["score"]
    tier_name = payload["tier"]
    tier_label = payload["tier_label"]
    red_flags = payload["red_flags"]
    followups = payload.get("next_crewscore_checks") or []
    _, tier_color, _ = get_tier(total)

    if report:
        report_path = Path(report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_vendor_html(payload), encoding="utf-8")

    if as_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]CREWSCORE — AI Vendor Diligence Checklist[/bold]\n"
            f"Vendor: [bold]{name}[/bold]\n"
            "[dim]Self-attested responses only; not an audit or verdict.[/dim]",
            border_style="blue",
            expand=False,
        )
    )
    console.print()
    console.print(Panel("[bold]SELF-ATTESTED VENDOR CHECKLIST[/bold]", border_style="blue", expand=False))
    console.print(f"  Vendor: [bold]{name}[/bold]")
    console.print()

    for question, label, pts, key in results:
        bar_full = min(10, pts)
        bar_empty = 10 - bar_full
        bar = "=" * bar_full + "-" * bar_empty
        status_color = (
            "green" if pts == SCORE_YES else ("yellow" if pts == SCORE_DK else "red")
        )
        flag = "  <-- FOLLOW UP" if pts == SCORE_NO or (
            key in CRITICAL_KEYS and pts == SCORE_DK
        ) else ""
        console.print(
            f"  [{status_color}][{bar}] {label:<12}[/{status_color}] {question}{flag}"
        )

    console.print()
    console.print(f"  [{'=' * 54}]")
    console.print(
        f"  [{tier_color}]CHECKLIST RESPONSE TOTAL: {total}/100 -- {tier_name} ({tier_label})[/{tier_color}]"
    )
    console.print(f"  [{'=' * 54}]")

    if red_flags:
        console.print()
        console.print(
            f"  [red]{len(red_flags)} RESPONSE GAP(S) need follow-up.[/red] "
            "Request evidence before making a vendor decision."
        )
        for flag in red_flags:
            console.print(f"  [red]•[/red] {flag}")

    if followups:
        console.print()
        console.print(
            "  [bold]Suggested CrewScore follow-ups[/bold] "
            "[dim](your prompts/CI — not a vendor grade)[/dim]"
        )
        for item in followups:
            dims = ", ".join(item.get("dimensions") or []) or "n/a"
            console.print(
                f"  [cyan]•[/cyan] {item.get('from_question', '')} "
                f"[dim]-> dimensions: {dims}[/dim]"
            )
            if item.get("suggested_cli"):
                console.print(f"    [dim]{item['suggested_cli']}[/dim]")

    console.print()
    console.print(
        "  [dim]Self-attested answers — not an independent audit, certification, or vendor verdict.[/dim]"
    )
    console.print("  Scored with CrewScore | pip install crewscore")
    console.print(f"  {HOMEPAGE} · {REPO}")
    console.print()

    console.print(f"  [{'=' * 54}]")
    console.print("  [bold]Ready-to-post LinkedIn copy:[/bold]")
    console.print(f"  [{'=' * 54}]")
    console.print()
    post = generate_linkedin_post(
        name,
        total,
        tier_name,
        [(q, a, p) for q, a, p, _ in results],
        red_flags=red_flags,
    )
    console.print(post)
    console.print()
    console.print("  [dim]Copy the text above and post it on LinkedIn.[/dim]")
    if report:
        console.print(f"  -> HTML report written to [bold]{report}[/bold]")
    console.print()
