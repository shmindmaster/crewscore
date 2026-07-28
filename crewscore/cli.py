"""CrewScore CLI — structural production-readiness scoring for AI agents."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from crewscore import __version__
from crewscore.export_eval import write_eval_stubs
from crewscore.report import render_badge_svg, render_html_report, share_text
from crewscore.rules_catalog import SCORING_METHOD, catalog_payload, scoring_transparency_block
from crewscore.scan import discover_prompt_files, score_paths
from crewscore.scoring import DIMENSIONS, RULESET_ID, build_result, tier_color
from crewscore.scorers import structural_analysis
from crewscore.smells import detect_smells, find_repo_root
from crewscore.profiles import (
    CODING_AGENT_CONFIG,
    PROFILE_LABELS,
    PROFILES,
    classify_path,
    governance_applies,
)
from crewscore.summary import format_scan_markdown, format_score_markdown
from crewscore.vendor_scorecard import assess_vendor

def _make_output_encodable() -> None:
    """Stop a stray non-ASCII character from crashing the CLI on Windows.

    When stdout is redirected on Windows it defaults to the ANSI code page
    (cp1252), and rich's legacy renderer writes straight through it — so a
    character like U+2192 raises UnicodeEncodeError and takes the whole
    command down. `crewscore rules --json > catalog.json` is a documented
    workflow, and Windows CI runners hit the same path.

    Degrading one glyph is always better than losing the command.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):  # closed or non-reconfigurable stream
            pass


_make_output_encodable()

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
    "--explain/--no-explain",
    default=True,
    help="Show matched/missing signals with rule IDs (default: on — scores are not a black box)",
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
@click.option(
    "--summary",
    type=click.Path(),
    default=None,
    help="Write GitHub-flavored markdown summary (PR/step comment body) to this path",
)
@click.option(
    "--profile",
    type=click.Choice(["auto", *PROFILES], case_sensitive=False),
    default="auto",
    help=(
        "Ruleset to judge by. auto (default) picks from the filename: "
        "coding-agent config (AGENTS.md, CLAUDE.md, .cursorrules) is judged on "
        "configuration smells; everything else on the 8 governance dimensions."
    ),
)
@click.option(
    "--max-smells",
    type=click.IntRange(0, 100),
    default=None,
    help=(
        "CI gate for coding-agent config: exit 2 if more than N configuration "
        "smells are found. Use instead of --threshold for AGENTS.md-style files."
    ),
)
def test(
    prompt,
    prompt_file,
    as_json,
    threshold,
    explain,
    report,
    badge,
    summary,
    profile,
    max_smells,
):
    """Run structural production-readiness analysis on an agent system prompt.

    Offline, deterministic regex scan — not live red-teaming.
    Every rule is public: run `crewscore rules` or `crewscore rules --json`.
    """
    system_prompt = None
    source = "prompt"
    prompt_path = None

    if prompt:
        system_prompt = prompt
        source = "prompt"
    elif prompt_file:
        prompt_path = Path(prompt_file)
        system_prompt = prompt_path.read_text(encoding="utf-8")
        source = str(prompt_file)
    else:
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        err_console.print(
            '[dim]Example: crewscore test --prompt "You are a helpful assistant..."[/dim]'
        )
        sys.exit(1)

    # Always compute findings so JSON is never a black box.
    dimensions, findings = structural_analysis.analyze_with_findings(system_prompt)
    # Smells need file context; a --prompt string only supports Context Bloat.
    smells = detect_smells(
        system_prompt,
        path=prompt_path,
        repo_root=find_repo_root(prompt_path),
    )
    resolved_profile = (
        classify_path(prompt_path) if profile == "auto" else profile.lower()
    )
    result = build_result(
        dimensions,
        mode="structural",
        source=source,
        prompt_text=system_prompt,
        smells=smells,
        profile=resolved_profile,
    )
    if threshold is not None and not result.governance_applicable:
        # CI always passes --json, where a console notice is invisible. The one
        # consumer whose gate just became a no-op has to learn it from the
        # payload, so record it as a warning rather than only printing it.
        result.warnings.append("threshold_ignored_for_config")

    if report:
        report_path = Path(report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            render_html_report(result, findings=findings),
            encoding="utf-8",
        )
    if badge:
        badge_path = Path(badge)
        badge_path.parent.mkdir(parents=True, exist_ok=True)
        badge_path.write_text(render_badge_svg(result), encoding="utf-8")

    md_body = format_score_markdown(result, findings=findings)
    if summary:
        summary_path = Path(summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(md_body, encoding="utf-8")
    # Always append to GitHub Actions job summary when running in GHA.
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as fh:
            fh.write(md_body)
            fh.write("\n")

    if as_json:
        payload = result.to_dict()
        if result.governance_applicable:
            # `findings` (matched/missing governance rules) and
            # `transparency` (the 15+85*matches/total_rules formula) are the
            # apparatus of a governance grade. Coding-agent config already
            # has `overall`/`dimensions` withheld; publishing these two would
            # let a reader reconstruct a score from them alone.
            payload["findings"] = findings
            payload["transparency"] = scoring_transparency_block()
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        color = tier_color(result.overall)
        console.print()
        console.print(
            Panel(
                f"[bold]{BRAND.upper()} — Structural Hygiene Report[/bold]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        console.print(
            f"[dim]Ruleset: [bold]{RULESET_ID}[/bold] · "
            "deterministic regex · no LLM · not a red-team[/dim]"
        )
        console.print(
            f"[dim]Artifact: [bold]{PROFILE_LABELS.get(result.profile, result.profile)}"
            "[/bold] · override with [bold]--profile[/bold][/dim]"
        )

        if not result.governance_applicable:
            # Governance dimensions on a build-instructions file are a category
            # error — measured at median 0/100 across 100 real repos.
            console.print()
            console.print(
                "  This is repo guidance for a coding agent, so it is judged on "
                "[bold]configuration smells[/bold], not on the production-"
                "governance dimensions."
            )
            console.print(
                "  [dim]Those dimensions (injection defense, human gates, audit, "
                "compliance) describe agents that act on a user's behalf. "
                "Scoring build instructions against them says nothing useful: "
                "measured across the 100 most-starred repos with an AGENTS.md, "
                "the median was 0/100.[/dim]"
            )
            console.print()
            console.print(f"  {'-' * 54}")
            console.print(f"  [bold]{result.tier}[/bold]")
            console.print(f"  {'-' * 54}")
        else:
            console.print(
                "[dim]How scored: each dimension = "
                "min(100, round(15+85×matches/total_rules)); "
                "overall = mean of 8 dimensions. "
                "List every rule: [bold]crewscore rules[/bold] "
                "· machine: [bold]crewscore rules --json[/bold][/dim]"
            )
            console.print()

            for label, key in DIMENSIONS:
                score = result.dimensions.get(key, 0)
                console.print(f"  {label:<32} {render_score_bar(score)}")

            console.print()
            console.print(f"  {'-' * 54}")
            console.print(
                f"  [{color}]OVERALL SCORE:  {result.overall}/100  "
                f"{result.tier}[/{color}]"
            )
            console.print(f"  {'-' * 54}")

        if result.warnings:
            console.print()
            for w in result.warnings:
                console.print(f"  [yellow]WARNING:[/yellow] {w}")
                if w == "template_boilerplate_detected":
                    console.print(
                        "  [dim]Score may be inflated by pasted CrewScore fix "
                        "templates — text coverage is not runtime safety.[/dim]"
                    )

        _render_smells(result.smells)

        if result.governance_applicable:
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
                            f"  [red]CRITICAL:[/red] No {label.lower()} signals matched."
                        )
                    else:
                        console.print(
                            f"  [dark_orange]WEAK:[/dark_orange] {label} is low "
                            f"({score}/100) — few open rules matched."
                        )

            if explain:
                _render_findings(findings)

        console.print()
        if result.governance_applicable:
            console.print(f"  Share: {share_text(result)}")
            console.print()
        console.print(
            f"  -> Open rules: [bold]crewscore rules[/bold] "
            f"(source: {SCORING_METHOD['source_of_truth']})"
        )
        if result.governance_applicable:
            console.print(
                f"  -> Run [bold]crewscore fix[/bold] to append templates "
                "(still not runtime proof)."
            )
            console.print(
                "  -> CI: [bold]--json --threshold N[/bold] · "
                "repo: [bold]crewscore scan .[/bold]"
            )
        else:
            console.print(
                "  -> CI: [bold]--json --max-smells N[/bold] · "
                "repo: [bold]crewscore scan .[/bold]"
            )
        if report:
            console.print(f"  -> HTML report written to [bold]{report}[/bold]")
        if badge:
            console.print(f"  -> SVG badge written to [bold]{badge}[/bold]")
        console.print(f"  -> {HOMEPAGE}")
        console.print()

    if result.governance_applicable:
        if threshold is not None and result.overall < threshold:
            if not as_json:
                err_console.print(
                    f"  [red]Threshold failure: {result.overall} < {threshold}[/red]"
                )
            sys.exit(2)
    elif threshold is not None and not as_json:
        # --threshold gates the governance score, which this artifact is not
        # judged on. Failing the build on it would fail every real AGENTS.md.
        # (The --json path carries `threshold_ignored_for_config` in warnings.)
        err_console.print(
            "  [yellow]--threshold ignored:[/yellow] coding-agent config is "
            "judged on configuration smells, not the governance score. "
            "Use --max-smells to gate CI."
        )

    # Smells stay out of every score, but --max-smells is an explicit request
    # to gate on them — and it has to mean the same thing here as in `scan`,
    # which applies it to every file regardless of profile.
    if max_smells is not None and len(result.smells) > max_smells:
        if not as_json:
            err_console.print(
                f"  [red]Smell threshold failure: {len(result.smells)} "
                f"> {max_smells}[/red]"
            )
        sys.exit(2)


_PROVENANCE_COLOR = {
    "evidence-backed": "green",
    "plausible": "yellow",
    "author-intuition": "dark_orange",
}


def _render_dimension_provenance(dim: dict) -> None:
    """Print a dimension's provenance grade, rationale, and citations."""
    grade = dim.get("grade")
    if not grade:
        return
    color = _PROVENANCE_COLOR.get(grade, "white")
    console.print(f"    provenance: [{color}]{grade}[/{color}]")
    rationale = dim.get("rationale")
    if rationale:
        console.print(f"    [dim]{rationale}[/dim]")
    for citation in dim.get("citations") or []:
        console.print(f"    [dim]· {citation}[/dim]")


def _render_smells(smells: list[dict]) -> None:
    """Print advisory configuration smells (never folded into the score)."""
    if not smells:
        return
    console.print()
    console.print(
        "[bold]Configuration smells[/bold] "
        "[dim](advisory — not part of the score)[/dim]"
    )
    for s in smells:
        console.print()
        console.print(
            f"  [yellow]{s['name']}[/yellow] [cyan]{s['smell_id']}[/cyan]"
        )
        console.print(f"    {s['detail']}")
        approx = " · approximation of the paper's LLM detector" if s.get(
            "approximates_paper"
        ) else ""
        console.print(
            f"    [dim]heuristic: {s['heuristic']} · "
            f"{s['paper_prevalence']}{approx}[/dim]"
        )
    console.print()
    console.print(f"  [dim]Source: {smells[0]['citation']}[/dim]")


def _render_findings(findings: list[dict]) -> None:
    """Print matched/missing findings with rule IDs (transparency)."""
    label_by_key = {key: label for label, key in DIMENSIONS}
    by_dim: dict[str, list[dict]] = {}
    for f in findings:
        by_dim.setdefault(f["dimension"], []).append(f)

    console.print()
    console.print(
        "[bold]Findings (open rule IDs · matched vs missing)[/bold]"
    )
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
            rid = f.get("rule_id")
            rid_s = f"[cyan]{rid}[/cyan] " if rid else ""
            if status == "matched":
                detail = snippet or reason
                console.print(f"    [green]matched[/green]  {rid_s}{detail}")
            else:
                console.print(f"    [red]missing[/red]  {rid_s}{reason}")


@main.command("rules")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit full open rule catalog as JSON",
)
@click.option(
    "--dimension",
    "-d",
    default=None,
    type=click.Choice([k for _, k in DIMENSIONS], case_sensitive=True),
    help="Filter to one dimension key",
)
def rules_cmd(as_json: bool, dimension: str | None):
    """List every scoring rule — CrewScore is not a black box.

    Prints the ruleset id, scoring formula, and each rule_id + regex.
    Machine form: crewscore rules --json
    """
    payload = catalog_payload(dimension=dimension)
    if as_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{BRAND} — Open scoring rules[/bold]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print()
    console.print(f"  Ruleset: [bold]{payload['ruleset']}[/bold]")
    console.print(f"  Type: {payload['method']['type']} · LLM calls: no · API key: no")
    console.print(f"  Source of truth: [bold]{payload['method']['source_of_truth']}[/bold]")
    console.print()
    console.print("[bold]Formula[/bold]")
    console.print(f"  Dimension: {payload['method']['dimension_score_formula']}")
    console.print(f"  Overall:   {payload['method']['overall_score_formula']}")
    console.print()
    console.print("[bold]This is NOT[/bold]")
    for line in payload["method"]["what_this_is_not"]:
        console.print(f"  · {line}")

    console.print()
    console.print("[bold]Provenance — where these rules come from[/bold]")
    for grade, meaning in payload["provenance_grades"].items():
        console.print(f"  [{_PROVENANCE_COLOR.get(grade, 'white')}]{grade}[/] — {meaning}")

    console.print()
    console.print(f"[bold]Rules ({payload['rule_count']})[/bold]")
    provenance_by_dim = {d["key"]: d for d in payload["dimensions"]}
    current_dim = None
    for r in payload["rules"]:
        if r["dimension"] != current_dim:
            current_dim = r["dimension"]
            console.print()
            console.print(
                f"  [bold]{r['dimension_label']}[/bold] ({r['dimension']})"
            )
            _render_dimension_provenance(provenance_by_dim.get(current_dim, {}))
        label = r.get("label") or ""
        label_s = f" — {label}" if label else ""
        console.print(f"    [cyan]{r['rule_id']}[/cyan]{label_s}")
        console.print(f"      [dim]/{r['pattern']}/i[/dim]")
    console.print()
    console.print(
        "  Machine-readable: [bold]crewscore rules --json[/bold]"
    )
    console.print()


@main.command("export-eval")
@click.option("--prompt", "-p", help="System prompt string to export")
@click.option(
    "--prompt-file",
    "-f",
    type=click.Path(exists=True),
    help="Path to system prompt file",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./crewscore-eval",
    help="Directory for Promptfoo / garak handoff stubs (default: ./crewscore-eval)",
)
def export_eval(prompt, prompt_file, output_dir):
    """Write live-eval stubs (Promptfoo config + garak notes) after structural gate.

    Does not run Promptfoo or garak. Honest handoff only.
    """
    if prompt:
        system_prompt = prompt
        source = "prompt"
    elif prompt_file:
        system_prompt = Path(prompt_file).read_text(encoding="utf-8")
        source = str(prompt_file)
    else:
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        sys.exit(1)

    paths = write_eval_stubs(
        Path(output_dir),
        system_prompt=system_prompt,
        prompt_source=source,
    )
    console.print()
    console.print(
        Panel(
            "[bold]Live eval handoff stubs[/bold]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print()
    for p in paths:
        console.print(f"  [green]wrote[/green] {p}")
    console.print()
    console.print(
        "  [dim]CrewScore remains structural only. "
        "Run Promptfoo/garak yourself — see README-EVAL.md[/dim]"
    )
    console.print()


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
    "--plan",
    "--dry-run",
    "plan",
    is_flag=True,
    default=False,
    help="List planned fix dimensions without writing (dry-run)",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit JSON summary of applied dimensions and score delta",
)
@click.option(
    "--profile",
    type=click.Choice(["auto", *PROFILES], case_sensitive=False),
    default="auto",
    help=(
        "Ruleset to treat the file as. auto (default) declines to write "
        "governance templates into coding-agent config (AGENTS.md, CLAUDE.md, "
        ".cursorrules); pass system_prompt to force them."
    ),
)
def fix(prompt, prompt_file, apply, output, plan, as_json, profile):
    """Append recommended guardrail patterns to a system prompt."""
    from crewscore.scorers.fix_patterns import (
        apply_fixes,
        explain_fixes,
        fix_cost_report,
        generate_fixes,
    )

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

    if plan and (apply or output):
        err_console.print(
            "[red]Error: --plan/--dry-run is mutually exclusive with "
            "--apply and --output[/red]"
        )
        sys.exit(1)

    resolved_profile = (
        classify_path(source_path) if profile == "auto" else profile.lower()
    )
    if not governance_applies(resolved_profile):
        # Every fix template is a governance template (HIPAA language, human
        # approval gates, audit trails). Injecting them into build instructions
        # is the same category error as grading that file 0/100 — and here it
        # would write the mistake into the user's repo. Decline loudly rather
        # than no-op: someone who ran `fix` is owed a reason and a next step.
        smell_verdict_cmd = (
            f"crewscore test --prompt-file {source_path}"
            if source_path
            else "crewscore test --prompt <your prompt text>"
        )
        reason = (
            "coding-agent config is judged on configuration smells, not the "
            "governance dimensions these templates target. See the smell "
            f"verdict with `{smell_verdict_cmd}`, gate CI with "
            "`--max-smells N`, or re-run with `--profile system_prompt` to "
            "force the templates in anyway."
        )
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "refused": True,
                        "reason": reason,
                        "profile": resolved_profile,
                        "governance_applicable": False,
                        "fixes_planned": [],
                        "fixes_applied": [],
                        "written": False,
                        "path": str(source_path) if source_path else None,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            err_console.print()
            err_console.print(
                "  [yellow]Refusing to fix coding-agent config:[/yellow] "
                f"{PROFILE_LABELS.get(resolved_profile, resolved_profile)} is "
                "judged on configuration smells, not the governance dimensions "
                "these templates target."
            )
            err_console.print(
                f"  -> Smell verdict: [bold]{smell_verdict_cmd}[/bold]"
            )
            err_console.print(
                "  -> Gate CI on it: [bold]--max-smells N[/bold]"
            )
            err_console.print(
                "  -> Force the templates anyway: "
                "[bold]--profile system_prompt[/bold]"
            )
            err_console.print()
        sys.exit(1)

    # The refusal above advertises --profile system_prompt as an escape hatch,
    # which makes this the path a rushed user takes. It stays unblocked (the
    # flag is explicit per invocation), but it must not be silent — on the
    # console *or* in the payload an automated retry loop reads.
    forced_governance_write = (
        source_path is not None
        and classify_path(source_path) == CODING_AGENT_CONFIG
        and resolved_profile != CODING_AGENT_CONFIG
    )
    if forced_governance_write and not as_json:
        # Say what this mode actually does. --plan and plain preview write
        # nothing, and --output writes somewhere else entirely; claiming a
        # write to the config file in those modes is simply false.
        if apply:
            action = f"writing governance templates to {source_path}"
        elif output:
            action = f"writing governance templates to {output}"
        elif plan:
            action = (
                f"planning governance templates for {source_path} "
                "(nothing is written in --plan mode)"
            )
        else:
            action = (
                f"previewing governance templates for {source_path} "
                "(nothing is written without --apply or --output)"
            )
        err_console.print(
            f"  [yellow]Note:[/yellow] {action}, which classifies as "
            "coding-agent config."
        )

    before = structural_analysis.analyze(system_prompt)
    before_result = build_result(
        before, source=str(source_path) if source_path else "prompt",
        profile=resolved_profile,
    )
    fixes = generate_fixes(before)

    honesty_note = (
        "Templates must be paired with runtime gates "
        "(tool allowlists, human approval hooks, logging, and policy enforcement)"
    )

    if plan:
        planned = list(fixes.keys())
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "fixes_planned": planned,
                        "before": before_result.to_dict(),
                        "written": False,
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
                f"[bold]{BRAND.upper()} — Fix Plan (dry-run)[/bold]",
                border_style="cyan",
                expand=False,
            )
        )
        console.print()
        if not planned:
            console.print(
                "  [green]No fixes needed — structural score is already strong.[/green]"
            )
        else:
            console.print(
                f"  [cyan]Would apply[/cyan] templates for {len(planned)} dimension(s):"
            )
            for key in planned:
                console.print(f"    · {key}")
            console.print()
            console.print(explain_fixes(fixes, planned=True))
            console.print()
            console.print(
                "[dim]Plan only — file not modified. "
                "Re-run without --plan and with --apply or --output to write.[/dim]"
            )
            console.print(
                "[yellow]Honesty note:[/yellow] Templates must be paired with "
                "runtime gates (tool allowlists, human approval hooks, logging)."
            )
        console.print()
        return

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
    after_result = build_result(
        after, source=str(source_path) if source_path else "prompt",
        profile=resolved_profile,
    )
    cost = fix_cost_report(system_prompt, enhanced)

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
                    "context_cost": cost,
                    # Mirrors the `refused: true` precedent above: a retry loop
                    # that took the advertised --profile system_prompt escape
                    # hatch gets a record that it overrode the classification.
                    "forced_governance_write": forced_governance_write,
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
        f"  [bold]Context cost:[/bold] +{cost['lines_added']} lines "
        f"({cost['lines_before']} -> {cost['lines_after']}). "
        "Every line is re-read on every run."
    )
    for warning in cost["warnings"]:
        console.print(f"  [yellow]WARNING:[/yellow] {warning}")
    console.print()
    console.print(
        "[yellow]Honesty note:[/yellow] These are prompt templates — "
        "they must be paired with runtime gates (tool allowlists, human "
        "approval hooks, logging, and policy enforcement) to have real effect. "
        "They are also generic: measured value comes from project-specific "
        "guidance, so specialise them rather than shipping them verbatim."
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
    help=(
        "Exit 2 if any system-prompt file scores below this. Coding-agent "
        "config is exempt — it is judged on smells, not the governance score."
    ),
)
@click.option(
    "--max-smells",
    type=click.IntRange(0, 100),
    default=None,
    help="Exit 2 if any file has more than N configuration smells",
)
@click.option(
    "--explain",
    is_flag=True,
    help="Show matched vs missing signals for the lowest-scoring file",
)
@click.option(
    "--summary",
    type=click.Path(),
    default=None,
    help="Write GitHub-flavored markdown summary (PR/step comment body) to this path",
)
@click.option(
    "--profile",
    type=click.Choice(["auto", *PROFILES], case_sensitive=False),
    default="auto",
    help=(
        "Ruleset to judge every scanned file by. auto (default) classifies each "
        "path: coding-agent config (AGENTS.md, CLAUDE.md, .cursorrules) is judged "
        "on configuration smells, everything else on the 8 governance dimensions."
    ),
)
def scan(path, as_json, threshold, max_smells, explain, summary, profile):
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

    forced_profile = None if profile == "auto" else profile.lower()
    scored = score_paths(files, profile=forced_profile)

    if threshold is not None:
        # Same warning key `test` emits, for the same reason: the Action passes
        # --threshold unconditionally and the docs recommend scan-path, so the
        # most-recommended CI setup loses its gate on every exempt file. CI
        # reads --json and the sticky PR comment, not the console.
        for item in scored:
            if not item.get("governance_applicable", True):
                item.setdefault("warnings", []).append(
                    "threshold_ignored_for_config"
                )

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

    md_body = format_scan_markdown(scored)
    if summary:
        summary_path = Path(summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(md_body, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open(
            "a", encoding="utf-8"
        ) as fh:
            fh.write(md_body)
            fh.write("\n")

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

        any_smells = any(item.get("smells") for item in scored)
        any_config = any(not item.get("governance_applicable", True) for item in scored)

        table = Table(show_header=True, header_style="bold")
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Artifact")
        table.add_column("Score", justify="right")
        table.add_column("Verdict")
        if any_smells:
            table.add_column("Smells")

        for item in scored:
            governed = item.get("governance_applicable", True)
            color = tier_color(item["overall"]) if governed else "cyan"
            row = [
                item["path"],
                "prompt" if governed else "config",
                # A governance score on a config file is not a verdict; showing
                # a number there is what made every real AGENTS.md look broken.
                f"[{color}]{item['overall']}[/{color}]" if governed else "[dim]n/a[/dim]",
                f"[{color}]{item['tier']}[/{color}]",
            ]
            if any_smells:
                names = [s["name"] for s in item.get("smells", [])]
                row.append(f"[yellow]{', '.join(names)}[/yellow]" if names else "")
            table.add_row(*row)

        console.print(table)
        console.print()

        if any_config:
            console.print(
                "  [dim]config = repo guidance for a coding agent (AGENTS.md, "
                "CLAUDE.md, .cursorrules). Judged on configuration smells, not "
                "the governance score. Override with [bold]--profile[/bold].[/dim]"
            )
        if any_smells:
            console.print(
                "  [dim]Smells are advisory and never affect the score. "
                "Detail: [bold]crewscore test --prompt-file <path>[/bold][/dim]"
            )
        if any_config or any_smells:
            console.print()

        # `--json` already carries `threshold_ignored_for_config` per file, and
        # `test` prints the same notice on its console path. `scan` printed
        # nothing here, so a config-only directory looked like a clean pass
        # with a --threshold gate that silently did nothing.
        ignored_paths = [
            item["path"]
            for item in scored
            if "threshold_ignored_for_config" in item.get("warnings", [])
        ]
        if ignored_paths:
            console.print(
                f"  [yellow]--threshold ignored[/yellow] on "
                f"{len(ignored_paths)} file(s): coding-agent config is judged "
                "on configuration smells, not the governance score. Use "
                "[bold]--max-smells[/bold] to gate CI on them."
            )
            console.print()

        # Explain only makes sense where a governance score is a verdict.
        governed = [i for i in scored if i.get("governance_applicable", True)]
        if explain and governed:
            worst = min(governed, key=lambda r: r["overall"])
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
            "[bold]--threshold N[/bold] gates prompts; "
            "[bold]--max-smells N[/bold] gates config files."
        )
        console.print(f"  -> {HOMEPAGE}")
        console.print()

    failed = False
    if threshold is not None:
        # Only files actually judged on the governance score can fail it.
        below = [
            item
            for item in scored
            if item.get("governance_applicable", True)
            and item["overall"] < threshold
        ]
        if below:
            failed = True
            if not as_json:
                for item in below:
                    err_console.print(
                        f"  [red]Threshold failure: {item['path']} "
                        f"{item['overall']} < {threshold}[/red]"
                    )

    if max_smells is not None:
        over = [item for item in scored if len(item.get("smells", [])) > max_smells]
        if over:
            failed = True
            if not as_json:
                for item in over:
                    err_console.print(
                        f"  [red]Smell threshold failure: {item['path']} "
                        f"{len(item['smells'])} > {max_smells}[/red]"
                    )

    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()

