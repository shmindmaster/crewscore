"""
AI Vendor Scorecard — assess an AI vendor's production credibility via a checklist.

Non-technical. No API key. Produces a score and optional shareable copy.
"""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

HOMEPAGE = "https://crewscore.ai"
REPO = "https://github.com/shmindmaster/crewscore"

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

SCORE_YES = 10
SCORE_DK = 3
SCORE_NO = 0

TIERS = [
    (80, "TRUSTED", "green", "Production-Proven"),
    (50, "CAUTION", "yellow", "Proceed Carefully"),
    (30, "HIGH RISK", "dark_orange", "Due Diligence Required"),
    (0, "RED FLAG", "red", "Walk Away"),
]


def get_tier(score: int) -> tuple[str, str, str]:
    for threshold, name, color, label in TIERS:
        if score >= threshold:
            return name, color, label
    return "RED FLAG", "red", "Walk Away"


def render_answer(ans: str) -> tuple[int, str]:
    normalized = ans.lower().strip()
    if normalized in ("y", "yes"):
        return SCORE_YES, "YES"
    if normalized in ("dk", "dont know", "don't know", "unsure"):
        return SCORE_DK, "DON'T KNOW"
    return SCORE_NO, "NO"


def generate_linkedin_post(
    vendor: str,
    score: int,
    tier: str,
    answers: list[tuple[str, str, int]],
) -> str:
    red_flags = [q for q, ans, pts in answers if pts == SCORE_NO]
    cautions = [q for q, ans, pts in answers if pts == SCORE_DK]

    lines = [
        f"We evaluated {vendor} for AI production use.",
        "",
        f"Score: {score}/100 -- {tier}",
        "",
    ]

    if red_flags:
        lines.append("Red flags:")
        for q in red_flags:
            lines.append(f"- {q.rstrip('?')}")
        lines.append("")

    if cautions:
        lines.append("Couldn't verify:")
        for q in cautions:
            lines.append(f"- {q.rstrip('?')}")
        lines.append("")

    lines.append("Before signing that contract, ask these 10 questions.")
    lines.append("")
    lines.append(f"Score yours: pip install crewscore && crewscore assess-vendor")
    lines.append(HOMEPAGE)
    lines.append("")
    lines.append("#AI #AIVendors #DueDiligence #EnterpriseAI #AIProcurement")

    return "\n".join(lines)


@click.command("assess-vendor")
@click.option("--name", "-n", required=True, help="Vendor/product name to assess")
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
def assess_vendor(name: str, answers: str | None, as_json: bool):
    """Score an AI vendor's production credibility. 10 questions. No API key."""

    results: list[tuple[str, str, int, str]] = []

    if answers:
        parts = [p.strip() for p in answers.split(",")]
        if len(parts) != 10:
            console.print(
                f"[red]Error: Expected 10 answers (y/n/dk), got {len(parts)}[/red]",
                err=True,
            )
            console.print(
                "[dim]Example: crewscore assess-vendor --name 'Acme AI' "
                "--answers 'y,y,n,dk,y,y,n,y,n,y'[/dim]",
                err=True,
            )
            raise SystemExit(1)
        for (question, key), ans in zip(QUESTIONS, parts):
            pts, label = render_answer(ans)
            results.append((question, label, pts, key))
    elif as_json:
        console.print(
            "[red]Error: --json requires --answers (non-interactive).[/red]",
            err=True,
        )
        raise SystemExit(1)
    else:
        console.print()
        console.print(
            Panel(
                f"[bold]CREWSCORE — AI Vendor Scorecard[/bold]\n"
                f"Assessing: [bold]{name}[/bold]",
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

    total = sum(pts for _, _, pts, _ in results)
    tier_name, tier_color, tier_label = get_tier(total)

    if as_json:
        payload = {
            "vendor": name,
            "score": total,
            "tier": tier_name,
            "tier_label": tier_label,
            "answers": [
                {
                    "question": q,
                    "key": key,
                    "answer": label,
                    "points": pts,
                }
                for q, label, pts, key in results
            ],
        }
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]CREWSCORE — AI Vendor Scorecard[/bold]\n"
            f"Assessing: [bold]{name}[/bold]",
            border_style="blue",
            expand=False,
        )
    )
    console.print()
    console.print(Panel("[bold]AI VENDOR SCORECARD[/bold]", border_style="blue", expand=False))
    console.print(f"  Vendor: [bold]{name}[/bold]")
    console.print()

    for question, label, pts, key in results:
        bar_full = min(10, pts)
        bar_empty = 10 - bar_full
        bar = "=" * bar_full + "-" * bar_empty
        status_color = (
            "green" if pts == SCORE_YES else ("yellow" if pts == SCORE_DK else "red")
        )
        flag = "  <-- RED FLAG" if pts == SCORE_NO else ""
        console.print(
            f"  [{status_color}][{bar}] {label:<12}[/{status_color}] {question}{flag}"
        )

    console.print()
    console.print(f"  [{'=' * 54}]")
    console.print(
        f"  [{tier_color}]SCORE: {total}/100 -- {tier_name} ({tier_label})[/{tier_color}]"
    )
    console.print(f"  [{'=' * 54}]")

    red_flag_count = sum(1 for _, _, pts, _ in results if pts == SCORE_NO)
    if red_flag_count > 0:
        console.print()
        console.print(
            f"  [red]{red_flag_count} RED FLAG(S) detected.[/red] "
            "Request evidence before signing."
        )

    console.print()
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
    )
    console.print(post)
    console.print()
    console.print("  [dim]Copy the text above and post it on LinkedIn.[/dim]")
    console.print()
