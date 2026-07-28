"""CrewScore CLI — structural production-readiness scoring for AI agents."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from crewscore import __version__
from crewscore.scoring import DIMENSIONS, build_result, tier_color
from crewscore.scorers import structural_analysis
from crewscore.vendor_scorecard import assess_vendor

console = Console()

BRAND = "CrewScore"
HOMEPAGE = "https://crewscore.ai"
REPO = "https://github.com/shmindmaster/crewscore"


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


@click.group()
@click.version_option(version=__version__, prog_name="crewscore")
def main():
    """CrewScore — offline structural scorecard for AI agent system prompts."""
    pass


main.add_command(assess_vendor)


@main.command()
@click.option("--prompt", "-p", help="System prompt string to test")
@click.option(
    "--prompt-file",
    "-f",
    type=click.Path(exists=True),
    help="Path to system prompt file",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit machine-readable JSON (for CI)",
)
@click.option(
    "--threshold",
    type=click.IntRange(0, 100),
    default=None,
    help="Exit non-zero if overall score is below this threshold",
)
def test(prompt, prompt_file, as_json, threshold):
    """Run structural production-readiness analysis on an agent system prompt.

    This mode is offline and free: it scans the prompt text for guardrail
    signals. It does not run live LLM adversarial attacks.
    """
    system_prompt = None
    source = "prompt"

    if prompt:
        system_prompt = prompt
        source = "prompt"
    elif prompt_file:
        system_prompt = Path(prompt_file).read_text(encoding="utf-8")
        source = str(prompt_file)
    else:
        console.print(
            "[red]Error: Provide --prompt or --prompt-file[/red]",
            err=True,
        )
        console.print(
            '[dim]Example: crewscore test --prompt "You are a helpful assistant..."[/dim]',
            err=True,
        )
        sys.exit(1)

    dimensions = structural_analysis.analyze(system_prompt)
    result = build_result(dimensions, mode="structural", source=source)

    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        color = tier_color(result.overall)
        console.print()
        console.print(
            Panel(
                f"[bold]{BRAND.upper()} — Structural Production Readiness Report[/bold]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        console.print(
            "[dim]Mode: structural (offline prompt scan). "
            "Not a substitute for live behavioral red-teaming.[/dim]"
        )
        console.print()

        for label, key in DIMENSIONS:
            score = result.dimensions.get(key, 0)
            console.print(f"  {label:<32} {render_score_bar(score)}")

        console.print()
        console.print(f"  {'-' * 54}")
        console.print(
            f"  [{color}]OVERALL SCORE:  {result.overall}/100  {result.tier}[/{color}]"
        )
        console.print(f"  {'-' * 54}")

        critical = [
            (label, key)
            for label, key in DIMENSIONS
            if result.dimensions.get(key, 0) < 50
        ]
        if critical:
            console.print()
            for label, key in critical:
                score = result.dimensions[key]
                if score == 0:
                    console.print(
                        f"  [red]CRITICAL:[/red] No {label.lower()} detected in your agent."
                    )
                else:
                    console.print(
                        f"  [dark_orange]WEAK:[/dark_orange] {label} is below "
                        f"production threshold ({score}/100)."
                    )

        console.print()
        console.print(
            f"  -> Run [bold]crewscore fix[/bold] to apply recommended guardrail patterns."
        )
        console.print(
            "  -> Re-run with [bold]--json[/bold] for CI. "
            "Use [bold]--threshold N[/bold] to fail builds below N."
        )
        console.print(f"  -> {HOMEPAGE}")
        console.print()

    if threshold is not None and result.overall < threshold:
        if not as_json:
            console.print(
                f"  [red]Threshold failure: {result.overall} < {threshold}[/red]",
                err=True,
            )
        sys.exit(2)


@main.command()
@click.option("--prompt", "-p", help="System prompt string to fix")
@click.option(
    "--prompt-file",
    "-f",
    type=click.Path(exists=True),
    help="Path to system prompt file",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Write the fixed prompt back to the file (in-place)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Write enhanced prompt to a new file",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit JSON summary of applied dimensions and score delta",
)
def fix(prompt, prompt_file, apply, output, as_json):
    """Append recommended guardrail patterns to a system prompt."""
    from crewscore.scorers.fix_patterns import apply_fixes, explain_fixes, generate_fixes

    system_prompt = None
    source_path = None

    if prompt:
        system_prompt = prompt
    elif prompt_file:
        source_path = Path(prompt_file)
        system_prompt = source_path.read_text(encoding="utf-8")
    else:
        console.print(
            "[red]Error: Provide --prompt or --prompt-file[/red]",
            err=True,
        )
        console.print(
            "[dim]Example: crewscore fix --prompt-file ./system-prompt.md --apply[/dim]",
            err=True,
        )
        sys.exit(1)

    before = structural_analysis.analyze(system_prompt)
    before_result = build_result(before)
    fixes = generate_fixes(before)

    if not fixes:
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "fixes_applied": [],
                        "before": before_result.to_dict(),
                        "after": before_result.to_dict(),
                        "message": "No fixes needed",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            console.print()
            console.print(
                "  [green]No fixes needed — structural score is already strong.[/green]"
            )
            console.print()
        return

    enhanced = apply_fixes(system_prompt, fixes)
    after = structural_analysis.analyze(enhanced)
    after_result = build_result(after)

    if apply and source_path:
        source_path.write_text(enhanced, encoding="utf-8")
    elif output:
        Path(output).write_text(enhanced, encoding="utf-8")

    if as_json:
        click.echo(
            json.dumps(
                {
                    "fixes_applied": list(fixes.keys()),
                    "before": before_result.to_dict(),
                    "after": after_result.to_dict(),
                    "written": bool(apply and source_path) or bool(output),
                    "path": str(source_path)
                    if apply and source_path
                    else (output or None),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{BRAND.upper()} — Applying Fixes[/bold]",
            border_style="green",
            expand=False,
        )
    )
    console.print()
    console.print(explain_fixes(fixes))
    console.print()

    if apply and source_path:
        console.print(f"  [green]Fixes applied in-place to {source_path}[/green]")
        console.print()
        console.print(
            f"  Score: [red]{before_result.overall}/100[/red] -> "
            f"[green]{after_result.overall}/100[/green] "
            f"(+{after_result.overall - before_result.overall})"
        )
        console.print()
    elif output:
        console.print(f"  [green]Enhanced prompt written to {output}[/green]")
        console.print()
        console.print(
            f"  Score: [red]{before_result.overall}/100[/red] -> "
            f"[green]{after_result.overall}/100[/green] "
            f"(+{after_result.overall - before_result.overall})"
        )
        console.print()
    else:
        console.print("[dim]--- Enhanced System Prompt ---[/dim]")
        console.print()
        console.print(enhanced)
        console.print()
        console.print("[dim]--- End ---[/dim]")
        console.print()
        console.print(
            "[dim]Use --apply to write in-place, or --output <file> to save to a new file.[/dim]"
        )
        console.print()


if __name__ == "__main__":
    main()
