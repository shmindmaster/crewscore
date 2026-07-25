"""
AI Vendor Scorecard - assess any AI vendor's production credibility in 2 minutes.
Non-technical. No API key. Shareable on LinkedIn/X.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

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

REASONS = {
    "vapor_demo": "Vapor demos fail on real data",
    "benchmark": "'99.9% accurate' means nothing without third-party proof",
    "certification": "Compliance theater vs. actual certification",
    "audit": "If you can't explain it to your board, you can't deploy it",
    "human_override": "No human gate = no enterprise deployment",
    "portability": "Trapped data = trapped budget",
    "pricing": "Token billing surprises are the #1 complaint in 2026",
    "security_audit": "'We take security seriously' is not proof",
    "production_refs": "Pilot != production. Everyone has pilots.",
    "incident": "It WILL fail. What happens next?",
}


def get_tier(score: int) -> tuple[str, str, str]:
    for threshold, name, color, label in TIERS:
        if score >= threshold:
            return name, color, label
    return "RED FLAG", "red", "Walk Away"


def render_answer(ans: str) -> tuple[int, str]:
    if ans.lower() in ("y", "yes"):
        return SCORE_YES, "YES"
    elif ans.lower() in ("dk", "dont know", "don't know", "unsure"):
        return SCORE_DK, "DON'T KNOW"
    else:
        return SCORE_NO, "NO"


def generate_linkedin_post(vendor: str, score: int, tier: str, answers: list[tuple[str, str, int]]) -> str:
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

    lines.append(f"Before signing that contract, ask these 10 questions.")
    lines.append("")
    lines.append("Score yours: pip install agent-guard && agent-guard assess-vendor")
    lines.append("")
    lines.append("#AI #AIVendors #DueDiligence #EnterpriseAI #AIProcurement")

    return "\n".join(lines)


@click.command("assess-vendor")
@click.option("--name", "-n", required=True, help="Vendor/product name to assess")
@click.option("--answers", "-a", help="Comma-separated answers (y/n/dk x10): 'y,y,n,dk,y,y,n,y,n,y'")
@click.option("--report", is_flag=True, help="Generate HTML report")
def assess_vendor(name: str, answers: str | None, report: bool):
    """Score an AI vendor's production credibility. 10 questions. 2 minutes. Zero technical knowledge needed."""

    console.print()
    console.print(Panel(
        f"[bold]AGENT GUARD - AI Vendor Scorecard[/bold]\n"
        f"Assessing: [bold]{name}[/bold]",
        border_style="blue",
        expand=False,
    ))
    console.print()

    results = []

    if answers:
        # Quick mode: batch answers
        parts = [p.strip() for p in answers.split(",")]
        if len(parts) != 10:
            console.print(f"[red]Error: Expected 10 answers (y/n/dk), got {len(parts)}[/red]")
            console.print("[dim]Example: agent-guard assess-vendor --name 'Acme AI' --answers 'y,y,n,dk,y,y,n,y,n,y'[/dim]")
            return
        for (question, key), ans in zip(QUESTIONS, parts):
            pts, label = render_answer(ans)
            results.append((question, label, pts, key))
    else:
        # Interactive mode
        console.print("[bold]Answer each question with y (yes), n (no), or dk (don't know)[/bold]")
        console.print()
        for i, (question, key) in enumerate(QUESTIONS, 1):
            console.print(f"  {i}. {question}")
            ans = input("     [y/n/dk]: ").strip()
            pts, label = render_answer(ans)
            results.append((question, label, pts, key))
            console.print()

    # Calculate score
    total = sum(pts for _, _, pts, _ in results)

    # Render scorecard
    console.print()
    console.print(Panel(f"[bold]AI VENDOR SCORECARD[/bold]", border_style="blue", expand=False))
    console.print(f"  Vendor: [bold]{name}[/bold]")
    console.print()

    tier_name, tier_color, tier_label = get_tier(total)

    for question, label, pts, key in results:
        filled = pts // 10 * 10 // 10  # 0 or 1 for bar
        bar_full = min(10, pts)
        bar_empty = 10 - bar_full
        bar = "=" * bar_full + "-" * bar_empty

        status_color = "green" if pts == SCORE_YES else ("yellow" if pts == SCORE_DK else "red")
        flag = "  <-- RED FLAG" if pts == SCORE_NO else ""

        console.print(f"  [{status_color}][{bar}] {label:<12}[/{status_color}] {question}{flag}")

    console.print()
    console.print(f"  [{'=' * 54}]")
    console.print(f"  [{tier_color}]SCORE: {total}/100 -- {tier_name} ({tier_label})[/{tier_color}]")
    console.print(f"  [{'=' * 54}]")

    red_flag_count = sum(1 for _, _, pts, _ in results if pts == SCORE_NO)
    if red_flag_count > 0:
        console.print()
        console.print(f"  [red]{red_flag_count} RED FLAG(S) detected.[/red] Request evidence before signing.")

    console.print()
    console.print("  Scored with agent-guard | pip install agent-guard")
    console.print("  https://github.com/shmindmaster/agent-guard")
    console.print()

    # Generate LinkedIn post
    console.print(f"  [{'=' * 54}]")
    console.print("  [bold]Ready-to-post LinkedIn copy:[/bold]")
    console.print(f"  [{'=' * 54}]")
    console.print()
    post = generate_linkedin_post(name, total, tier_name, [(q, a, p) for q, a, p, _ in results])
    console.print(post)
    console.print()
    console.print("  [dim]Copy the text above and post it on LinkedIn.[/dim]")
    console.print()
