"""agent-guard CLI - stress-test your AI agent in 30 seconds."""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from agent_guard import __version__
from agent_guard.scorers import structural_analysis
from agent_guard.vendor_scorecard import assess_vendor

console = Console()

DIMENSIONS = [
    ("Prompt Injection Resistance", "injection"),
    ("Hallucination Guardrails", "hallucination"),
    ("Source Citation Requirements", "citation"),
    ("Cost Runaway Protection", "cost"),
    ("Human-in-the-Loop Gates", "human_gate"),
    ("Safe-Stop Behavior", "safe_stop"),
    ("Audit Trail & Provenance", "audit"),
    ("Compliance Readiness", "compliance"),
]


def render_score_bar(score: int) -> str:
    filled = round(score / 10)
    empty = 10 - filled
    bar = "=" * filled + "-" * empty

    if score >= 90:
        color = "green"
        status = "PASS"
    elif score >= 70:
        color = "yellow"
        status = "MONITOR"
    elif score >= 50:
        color = "dark_orange"
        status = "WEAK"
    else:
        color = "red"
        status = "MISSING" if score == 0 else "FAILS"

    return f"[{color}][{bar}] {score:>3}/100[/{color}]  {status}"


def score_tier(overall: int) -> tuple[str, str]:
    if overall >= 90:
        return "green", "PRODUCTION READY"
    elif overall >= 70:
        return "yellow", "SHIP WITH MONITORING"
    elif overall >= 50:
        return "dark_orange", "NEEDS WORK"
    else:
        return "red", "NOT PRODUCTION READY"


@click.group()
@click.version_option(version=__version__, prog_name="agent-guard")
def main():
    """agent-guard - Stress-test your AI agent."""
    pass

main.add_command(assess_vendor)


@main.command()
@click.option("--prompt", "-p", help="System prompt string to test")
@click.option("--prompt-file", "-f", type=click.Path(exists=True), help="Path to system prompt file")
@click.option("--mode", type=click.Choice(["structural", "adversarial"]), default="structural",
              help="structural = offline (free), adversarial = live LLM (~$0.50)")
@click.option("--langgraph", type=click.Path(exists=True), help="Path to LangGraph agent definition")
@click.option("--crewai", type=click.Path(exists=True), help="Path to CrewAI crew definition")
def test(prompt, prompt_file, mode, langgraph, crewai):
    """Run production-readiness tests against an AI agent."""

    system_prompt = None
    if prompt:
        system_prompt = prompt
    elif prompt_file:
        system_prompt = Path(prompt_file).read_text()
    elif langgraph:
        system_prompt = f"[LANGGRAPH AGENT: {langgraph}]"
        console.print(f"[dim]Loading LangGraph agent from {langgraph}...[/dim]")
    elif crewai:
        system_prompt = f"[CREWAI CREW: {crewai}]"
        console.print(f"[dim]Loading CrewAI crew from {crewai}...[/dim]")
    else:
        console.print("[red]Error: Provide --prompt, --prompt-file, --langgraph, or --crewai[/red]")
        console.print("[dim]Example: agent-guard test --prompt \"You are a helpful assistant...\"[/dim]")
        sys.exit(1)

    if mode == "adversarial":
        console.print("[yellow]Adversarial mode requires an API key and costs ~$0.50 in tokens.[/yellow]")
        console.print("[yellow]  Set ANTHROPIC_API_KEY or OPENAI_API_KEY. Falling back to structural mode.[/yellow]\n")

    console.print()

    results = structural_analysis.analyze(system_prompt)

    console.print(Panel(
        "[bold]AGENT GUARD - Production Readiness Report[/bold]",
        border_style="blue",
        expand=False,
    ))
    console.print()

    for label, key in DIMENSIONS:
        score = results.get(key, 0)
        bar = render_score_bar(score)
        console.print(f"  {label:<32} {bar}")

    overall = sum(results.values()) // len(results)
    color, tier = score_tier(overall)
    console.print()
    console.print(f"  {'-' * 54}")
    console.print(f"  [{color}]OVERALL SCORE:  {overall}/100  {tier}[/{color}]")
    console.print(f"  {'-' * 54}")

    critical = [(label, key) for label, key in DIMENSIONS if results.get(key, 0) < 50]
    if critical:
        console.print()
        for label, key in critical:
            score = results[key]
            if score == 0:
                console.print(f"  [red]CRITICAL:[/red] No {label.lower()} detected in your agent.")
            else:
                console.print(f"  [dark_orange]WEAK:[/dark_orange] {label} is below production threshold ({score}/100).")

    console.print()
    console.print(f"  -> Run [bold]agent-guard fix[/bold] to apply recommended guardrail patterns.")
    console.print(f"  -> Report: [blue]https://agent-guard.dev/r/demo-001[/blue]")
    console.print()
    console.print(f"  [dim]Built by the team that operates 7 regulated AI systems -> [link=https://pendoah.ai]pendoah.ai[/link][/dim]")
    console.print()


@main.command()
@click.option("--prompt", "-p", help="System prompt string to fix")
@click.option("--prompt-file", "-f", type=click.Path(exists=True), help="Path to system prompt file")
@click.option("--apply", is_flag=True, help="Write the fixed prompt back to the file (in-place)")
@click.option("--output", "-o", type=click.Path(), help="Write enhanced prompt to a new file")
def fix(prompt, prompt_file, apply, output):
    """Apply recommended guardrail patterns to your agent's system prompt."""

    from agent_guard.scorers.fix_patterns import generate_fixes, apply_fixes, explain_fixes

    system_prompt = None
    source_path = None

    if prompt:
        system_prompt = prompt
    elif prompt_file:
        source_path = Path(prompt_file)
        system_prompt = source_path.read_text()
    else:
        console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        console.print("[dim]Example: agent-guard fix --prompt-file ./system-prompt.md --apply[/dim]")
        sys.exit(1)

    console.print()
    console.print(Panel(
        "[bold]AGENT GUARD - Applying Fixes[/bold]",
        border_style="green",
        expand=False,
    ))
    console.print()

    results = structural_analysis.analyze(system_prompt)
    fixes = generate_fixes(results)

    if not fixes:
        console.print("  [green]No fixes needed - your agent is production-ready.[/green]")
        console.print()
        return

    console.print(explain_fixes(fixes))
    console.print()

    enhanced = apply_fixes(system_prompt, fixes)

    if apply and source_path:
        source_path.write_text(enhanced)
        console.print(f"  [green]Fixes applied in-place to {source_path}[/green]")
        console.print()

        new_results = structural_analysis.analyze(enhanced)
        old_overall = sum(results.values()) // len(results)
        new_overall = sum(new_results.values()) // len(new_results)
        console.print(f"  Score: [red]{old_overall}/100[/red] -> [green]{new_overall}/100[/green] (+{new_overall - old_overall})")
        console.print()

    elif output:
        Path(output).write_text(enhanced)
        console.print(f"  [green]Enhanced prompt written to {output}[/green]")
        console.print()

    else:
        console.print("[dim]--- Enhanced System Prompt ---[/dim]")
        console.print()
        console.print(enhanced)
        console.print()
        console.print("[dim]--- End ---[/dim]")
        console.print()
        console.print("[dim]Use --apply to write in-place, or --output <file> to save to a new file.[/dim]")
        console.print()
