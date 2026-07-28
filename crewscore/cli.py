"""CrewScore CLI — structural production-readiness scoring for AI agents."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from crewscore import __version__
from crewscore.report import render_badge_svg, render_html_report, share_text
from crewscore.scan import discover_prompt_files, score_paths
from crewscore.scoring import DIMENSIONS, build_result, tier_color
from crewscore.scorers import structural_analysis
from crewscore.vendor_scorecard import assess_vendor

console = Console()
err_console = Console(stderr=True)

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
@click.option(
    "--explain",
    is_flag=True,
    help="Show matched vs missing guardrail signals per dimension",
)
@click.option(
    "--report",
    type=click.Path(),
    default=None,
    help="Write a self-contained HTML scorecard to this path",
)
@click.option(
    "--badge",
    type=click.Path(),
    default=None,
    help="Write an SVG badge to this path",
)
def test(prompt, prompt_file, as_json, threshold, explain, report, badge):
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
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        err_console.print(
            '[dim]Example: crewscore test --prompt "You are a helpful assistant..."[/dim]'
        )
        sys.exit(1)

    findings = None
    if explain:
        dimensions, findings = structural_analysis.analyze_with_findings(system_prompt)
    else:
        dimensions = structural_analysis.analyze(system_prompt)
    result = build_result(dimensions, mode="structural", source=source)

    if report:
        report_path = Path(report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_html_report(result), encoding="utf-8")
    if badge:
        badge_path = Path(badge)
        badge_path.parent.mkdir(parents=True, exist_ok=True)
        badge_path.write_text(render_badge_svg(result), encoding="utf-8")

    if as_json:
        payload = result.to_dict()
        if findings is not None:
            payload["findings"] = findings
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
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

        if findings is not None:
            _render_findings(findings)

        console.print()
        console.print(f"  Share: {share_text(result)}")
        console.print()
        console.print(
            f"  -> Run [bold]crewscore fix[/bold] to apply recommended guardrail patterns."
        )
        console.print(
            "  -> Re-run with [bold]--json[/bold] for CI. "
            "Use [bold]--threshold N[/bold] to fail builds below N."
        )
        if report:
            console.print(f"  -> HTML report written to [bold]{report}[/bold]")
        if badge:
            console.print(f"  -> SVG badge written to [bold]{badge}[/bold]")
        console.print(f"  -> {HOMEPAGE}")
        console.print()

    if threshold is not None and result.overall < threshold:
        if not as_json:
            err_console.print(
                f"  [red]Threshold failure: {result.overall} < {threshold}[/red]"
            )
        sys.exit(2)


def _render_findings(findings: list[dict]) -> None:
    """Print matched/missing findings grouped by dimension."""
    label_by_key = {key: label for label, key in DIMENSIONS}
    by_dim: dict[str, list[dict]] = {}
    for f in findings:
        by_dim.setdefault(f["dimension"], []).append(f)

    console.print()
    console.print("[bold]Findings (matched vs missing signals)[/bold]")
    for _, key in DIMENSIONS:
        items = by_dim.get(key, [])
        if not items:
            continue
        dim_label = label_by_key.get(key, key)
        console.print()
        console.print(f"  [bold]{dim_label}[/bold] ({key})")
        for f in items:
            status = f["status"]
            reason = f.get("pattern_or_reason") or ""
            snippet = f.get("snippet")
            if status == "matched":
                detail = snippet or reason
                console.print(f"    [green]matched[/green]  {detail}")
            else:
                console.print(f"    [red]missing[/red]  {reason}")



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
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        err_console.print(
            "[dim]Example: crewscore fix --prompt-file ./system-prompt.md --apply[/dim]"
        )
        sys.exit(1)

    before = structural_analysis.analyze(system_prompt)
    before_result = build_result(before)
    fixes = generate_fixes(before)

    honesty_note = (
        "Templates must be paired with runtime gates "
        "(tool allowlists, human approval hooks, logging, and policy enforcement)"
    )

    if not fixes:
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "fixes_applied": [],
                        "before": before_result.to_dict(),
                        "after": before_result.to_dict(),
                        "message": "No fixes needed",
                        "note": honesty_note,
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
                    "note": honesty_note,
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
    console.print(
        "[yellow]Honesty note:[/yellow] These are prompt templates — "
        "they must be paired with runtime gates (tool allowlists, human "
        "approval hooks, logging, and policy enforcement) to have real effect."
    )
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


@main.command("scan")
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit machine-readable JSON list of scored files",
)
@click.option(
    "--threshold",
    type=click.IntRange(0, 100),
    default=None,
    help="Exit 2 if any file's overall score is below this threshold",
)
@click.option(
    "--explain",
    is_flag=True,
    help="Show matched vs missing signals for the lowest-scoring file",
)
def scan(path, as_json, threshold, explain):
    """Discover and score agent prompt files under PATH (default: .).

    Looks for AGENTS.md, CLAUDE.md, system-prompt.md, and files under
    agents/prompts/prompt directories. Offline structural scan only.
    """
    root = Path(path).resolve()
    files = discover_prompt_files(root)

    if not files:
        err_console.print(
            f"[red]No agent prompt files found under {root}[/red]"
        )
        err_console.print(
            "[dim]Looking for AGENTS.md, CLAUDE.md, system-prompt.md, "
            "system_prompt.md, AGENT.md, prompts.md, and files under "
            "agents/, prompts/, or prompt/ directories.[/dim]"
        )
        sys.exit(1)

    scored = score_paths(files)

    # Prefer paths relative to scan root for display; keep abs for --explain.
    abs_by_rel: dict[str, Path] = {}
    for item in scored:
        abs_path = Path(item["path"]).resolve()
        try:
            rel = str(abs_path.relative_to(root))
        except ValueError:
            rel = str(abs_path)
        abs_by_rel[rel] = abs_path
        item["path"] = rel

    if as_json:
        click.echo(json.dumps(scored, indent=2, sort_keys=True))
    else:
        from rich.table import Table

        console.print()
        console.print(
            Panel(
                f"[bold]{BRAND.upper()} — Repo Prompt Scan[/bold]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        console.print(
            f"[dim]Scanned {root} — {len(scored)} file(s). "
            "Structural offline scores only.[/dim]"
        )
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Overall", justify="right")
        table.add_column("Tier")

        for item in scored:
            color = tier_color(item["overall"])
            table.add_row(
                item["path"],
                f"[{color}]{item['overall']}[/{color}]",
                f"[{color}]{item['tier']}[/{color}]",
            )

        console.print(table)
        console.print()

        if explain and scored:
            worst = min(scored, key=lambda r: r["overall"])
            worst_abs = abs_by_rel.get(worst["path"], root / worst["path"])
            text = worst_abs.read_text(encoding="utf-8", errors="replace")
            _dims, findings = structural_analysis.analyze_with_findings(text)
            console.print(
                f"[bold]Explain (lowest score):[/bold] {worst['path']} "
                f"({worst['overall']}/100)"
            )
            _render_findings(findings)
            console.print()

        console.print(
            "  -> Re-run with [bold]--json[/bold] for CI. "
            "Use [bold]--threshold N[/bold] to fail if any file is below N."
        )
        console.print(f"  -> {HOMEPAGE}")
        console.print()

    if threshold is not None:
        below = [item for item in scored if item["overall"] < threshold]
        if below:
            if not as_json:
                for item in below:
                    err_console.print(
                        f"  [red]Threshold failure: {item['path']} "
                        f"{item['overall']} < {threshold}[/red]"
                    )
            sys.exit(2)


if __name__ == "__main__":
    main()

