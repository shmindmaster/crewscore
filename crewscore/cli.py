"""CrewScore CLI — offline guardrail-coverage scoring for AI agents."""

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
from crewscore.policy import (
    PolicyError,
    baseline_payload,
    evaluate_policy,
    resolve_policy,
)
from crewscore.hero import coverage_from_findings, hero_missing_control
from crewscore.report import render_badge_svg, render_html_report, share_text
from crewscore.rules_catalog import SCORING_METHOD, catalog_payload, scoring_transparency_block
from crewscore.sarif import write_sarif
from crewscore.scan import (
    MAX_FILE_BYTES,
    discover_inline_prompt_sources,
    discover_prompt_files,
    score_inline_prompts,
    score_paths,
)
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

def _read_prompt_file(path: Path) -> str:
    """Read a prompt file without letting a bad file take the command down.

    `scan` has always been defensive here - a size cap plus errors="replace" -
    while `test`, `fix` and `export-eval` used a bare read_text. So the same
    bytes either scored or produced a raw UnicodeDecodeError traceback
    depending on which command you reached for, and that traceback appeared
    even under --json, where the caller is a machine that cannot read one.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        err_console.print(f"[red]Error: cannot read {path}: {exc.strerror or exc}[/red]")
        sys.exit(1)
    if size > MAX_FILE_BYTES:
        err_console.print(
            f"[red]Error: {path} is {size // 1024} KB; the size limit is "
            f"{MAX_FILE_BYTES // 1024} KB.[/red]"
        )
        err_console.print(
            "[dim]A prompt this large is usually a whole directory concatenated. "
            "Point --prompt-file at the prompt itself, or use `crewscore scan`.[/dim]"
        )
        sys.exit(1)
    try:
        # errors="replace" matches scan: one mangled glyph beats losing the run.
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        err_console.print(f"[red]Error: cannot read {path}: {exc.strerror or exc}[/red]")
        sys.exit(1)


console = Console()
err_console = Console(stderr=True)

BRAND = "CrewScore"
HOMEPAGE = "https://crewscore.ai"
REPO = "https://github.com/shmindmaster/crewscore"


def _resolve_policy_or_exit(
    *,
    config: str | None,
    require: tuple[str, ...],
    forbid_missing: tuple[str, ...],
    baseline: str | None,
    fail_on_regression: bool,
):
    """Resolve optional control policy with a clear CLI error, not a traceback."""
    try:
        return resolve_policy(
            config=config,
            require=require,
            forbid_missing=forbid_missing,
            baseline=baseline,
            fail_on_regression=fail_on_regression,
        )
    except PolicyError as exc:
        err_console.print(f"[red]Policy error: {exc}[/red]")
        sys.exit(1)


def _evaluate_policy_or_exit(settings, **kwargs):
    try:
        return evaluate_policy(settings, **kwargs)
    except PolicyError as exc:
        err_console.print(f"[red]Policy error: {exc}[/red]")
        sys.exit(1)


def _baseline_entries(root: Path, profile: str | None) -> list[tuple[str, str, list[dict]]]:
    """Collect public control state for a prompt-free baseline file."""
    entries: list[tuple[str, str, list[dict]]] = []
    for path in discover_prompt_files(root):
        resolved = profile or classify_path(path)
        if not governance_applies(resolved):
            continue
        text = _read_prompt_file(path)
        _dimensions, findings = structural_analysis.analyze_with_findings(text)
        entries.append((path.resolve().relative_to(root).as_posix(), resolved, findings))
    return entries


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
    """CrewScore — offline guardrail-coverage checks for AI agent prompts and config."""
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
@click.option(
    "--require",
    "required_controls",
    multiple=True,
    help=(
        "Require a public control ID or a whole dimension (comma-separated; "
        "repeatable). This is an explicit policy gate, not a score threshold."
    ),
)
@click.option(
    "--forbid-missing",
    "forbidden_missing_controls",
    multiple=True,
    help="Fail if a named public control ID or dimension is not detected (repeatable).",
)
@click.option(
    "--baseline",
    type=click.Path(dir_okay=False),
    default=None,
    help="Prompt-free baseline JSON written by `crewscore baseline`.",
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    help="Fail only when a control recorded in the baseline disappears.",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Read required controls and baseline settings from .crewscore.yml.",
)
@click.option(
    "--sarif",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write prompt-free missing-control findings as SARIF 2.1.0.",
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
    required_controls,
    forbidden_missing_controls,
    baseline,
    fail_on_regression,
    config,
    sarif,
):
    """Measure governance guardrail coverage in an agent system prompt.

    Offline, deterministic regex scan — not live red-teaming.
    The score is coverage, not quality: it reports which controls are written
    down, not whether the agent obeys them. See docs/validation.md.
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
        system_prompt = _read_prompt_file(prompt_path)
        source = str(prompt_file)
    else:
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        err_console.print(
            '[dim]Example: crewscore test --prompt "You are a helpful assistant..."[/dim]'
        )
        sys.exit(1)

    policy = _resolve_policy_or_exit(
        config=config,
        require=required_controls,
        forbid_missing=forbidden_missing_controls,
        baseline=baseline,
        fail_on_regression=fail_on_regression,
    )

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

    policy_result = _evaluate_policy_or_exit(
        policy,
        findings=findings,
        governance_applicable=result.governance_applicable,
        source=str(prompt_path) if prompt_path else "prompt",
        root=prompt_path.parent if prompt_path else None,
    )

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
    if sarif:
        write_sarif(
            sarif,
            [
                (
                    str(prompt_path) if prompt_path else "prompt",
                    result.governance_applicable,
                    findings,
                )
            ],
        )

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

    matched_n = total_n = 0
    hero = None
    if result.governance_applicable:
        matched_n, total_n = coverage_from_findings(findings)
        hero = hero_missing_control(findings)

    if as_json:
        payload = result.to_dict()
        if result.governance_applicable:
            # `findings` (matched/missing governance rules) and
            # `transparency` (the controls-covered formula) are the
            # apparatus of a governance grade. Coding-agent config already
            # has `overall`/`dimensions` withheld; publishing these two would
            # let a reader reconstruct a score from them alone.
            payload["findings"] = findings
            payload["transparency"] = scoring_transparency_block()
            payload["coverage"] = {
                "matched": matched_n,
                "total": total_n,
                "missing": total_n - matched_n,
                "hero": hero,
            }
        if policy.enabled:
            payload["policy"] = policy_result
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        color = tier_color(result.overall)
        console.print()
        console.print(
            Panel(
                f"[bold]{BRAND.upper()} — Written Control Coverage[/bold]",
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
                "the share of that dimension's controls your prompt states; "
                "overall = mean of 8 dimensions. "
                "Coverage count = matched / 23 published controls. "
                "See: [bold]crewscore rules --concepts[/bold] "
                "· machine: [bold]crewscore rules --json[/bold][/dim]"
            )
            console.print()

            for label, key in DIMENSIONS:
                score = result.dimensions.get(key, 0)
                console.print(f"  {label:<32} {render_score_bar(score)}")

            console.print()
            console.print(f"  {'-' * 54}")
            console.print(
                f"  [{color}]CONTROL COVERAGE:  {matched_n}/{total_n} written  "
                f"({result.overall}/100 mean)  {result.tier}[/{color}]"
            )
            console.print(f"  {'-' * 54}")
            if hero:
                console.print()
                console.print(
                    f"  [bold red]FIRST GAP TO REVIEW:[/bold red] {hero.get('label')}"
                )
                if hero.get("concept"):
                    console.print(
                        f"  [dim]Gate CI on it: "
                        f"[bold]crewscore scan . --require {hero['concept']}"
                        f"[/bold][/dim]"
                    )

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
            console.print(
                "  Share: "
                + share_text(
                    result,
                    matched=matched_n,
                    total=total_n,
                    hero_label=(hero or {}).get("label"),
                )
            )
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
            if hero and hero.get("concept"):
                console.print(
                    f"  -> CI (one control): [bold]crewscore scan . "
                    f"--require {hero['concept']}[/bold]"
                )
            console.print(
                "  -> CI: [bold]--json --fail-on-regression --baseline FILE[/bold] · "
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
        # Failure reasons always reach stderr, including --json runs: an exit
        # code 2 with a silent log is why CI gates get deleted instead of
        # fixed. stdout stays pure JSON.
        err_console.print(
            f"  [red]Smell threshold failure: {len(result.smells)} "
            f"> {max_smells}[/red]"
        )
        sys.exit(2)

    if policy_result["failed"]:
        missing = policy_result.get("missing_required_controls") or []
        regressions = policy_result.get("regressed_controls") or []
        if missing:
            err_console.print(
                "  [red]Required-control failure:[/red] " + ", ".join(missing)
            )
        if regressions:
            err_console.print(
                "  [red]Regression failure:[/red] " + ", ".join(regressions)
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
    "--concepts",
    "show_concepts",
    is_flag=True,
    help="Show the controls each dimension scores on (the score denominator)",
)
@click.option(
    "--dimension",
    "-d",
    default=None,
    type=click.Choice([k for _, k in DIMENSIONS], case_sensitive=True),
    help="Filter to one dimension key",
)
def rules_cmd(as_json: bool, show_concepts: bool, dimension: str | None):
    """List every scoring rule — CrewScore is not a black box.

    Prints the ruleset id, scoring formula, and each rule_id + regex.

    A dimension scores on how many of its *controls* the prompt states, and
    several rules can be alternative phrasings of one control. Run
    `crewscore rules --concepts` to see that grouping — it is the denominator
    of every dimension score.

    Machine form: crewscore rules --json
    """
    payload = catalog_payload(dimension=dimension)
    if as_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    if show_concepts:
        console.print()
        console.print(
            Panel(
                f"[bold]{BRAND} — Controls each dimension scores on[/bold]",
                border_style="cyan",
                expand=False,
            )
        )
        console.print()
        console.print(f"  {payload['method']['dimension_score_formula']}")
        console.print()
        current = None
        for c in payload["concepts"]:
            if c["dimension"] != current:
                current = c["dimension"]
                total = sum(
                    1 for x in payload["concepts"] if x["dimension"] == current
                )
                console.print()
                console.print(
                    f"  [bold]{c['dimension_label']}[/bold] ({current}) — "
                    f"{total} controls, {c['points']} points each"
                )
            console.print(f"    [cyan]{c['label']}[/cyan]")
            console.print(
                f"      [dim]{c['concept']} · any of: "
                f"{', '.join(c['rule_ids'])}[/dim]"
            )
        console.print()
        console.print(
            f"  {payload['control_count']} controls across "
            f"{payload['rule_count']} rules. "
            "Rules within a control are alternative phrasings — stating one "
            "control several ways scores it once."
        )
        console.print()
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
    help="Directory for Promptfoo / garak handoff artifacts (default: ./crewscore-eval)",
)
@click.option(
    "--provider",
    default="openai:gpt-4o-mini",
    show_default=True,
    help="Promptfoo provider id placeholder (not called by CrewScore).",
)
def export_eval(prompt, prompt_file, output_dir, provider):
    """Write live-eval handoff artifacts from structural gaps.

    Scores the prompt offline, then writes Promptfoo config, garak notes, and a
    prompt-free JSON manifest biased toward missing written controls.

    Does not run Promptfoo or garak.
    """
    if prompt:
        system_prompt = prompt
        source = "prompt"
    elif prompt_file:
        system_prompt = _read_prompt_file(Path(prompt_file))
        source = str(prompt_file)
    else:
        err_console.print("[red]Error: Provide --prompt or --prompt-file[/red]")
        sys.exit(1)

    paths = write_eval_stubs(
        Path(output_dir),
        system_prompt=system_prompt,
        prompt_source=source,
        provider=provider,
    )
    console.print()
    console.print(
        Panel(
            "[bold]Live eval handoff[/bold]\n"
            "[dim]Structural gaps mapped to starter Promptfoo cases + garak probes. "
            "CrewScore does not run either tool.[/dim]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print()
    for p in paths:
        console.print(f"  [green]wrote[/green] {p}")
    console.print()
    console.print(
        "  [dim]Next: edit providers in promptfooconfig.yaml, then "
        "npx promptfoo@latest eval — see README-EVAL.md[/dim]"
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
        NO_FIXES_COVERAGE_MESSAGE,
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
        system_prompt = _read_prompt_file(source_path)
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
        # The classification clause names the SOURCE. Hanging it off `action`
        # made --output read as though the destination were the config file.
        # Every mode but --output has already named the source, so only that
        # one needs to repeat it.
        subject = str(source_path) if output else "It"
        err_console.print(
            f"  [yellow]Note:[/yellow] {action}. {subject} classifies as "
            "coding-agent config, which these governance templates do not "
            "target."
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
                        # Same record as the write payload, for the same
                        # reason: --plan is exactly where a consumer previews
                        # this override before it happens.
                        "forced_governance_write": forced_governance_write,
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
                f"  [green]{NO_FIXES_COVERAGE_MESSAGE}[/green]"
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
                        "forced_governance_write": forced_governance_write,
                        "note": honesty_note,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            console.print()
            console.print(
                f"  [green]{NO_FIXES_COVERAGE_MESSAGE}[/green]"
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


@main.command("baseline")
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Destination JSON path (default: PATH/.crewscore-baseline.json).",
)
@click.option(
    "--profile",
    type=click.Choice([*PROFILES], case_sensitive=False),
    default=None,
    help="Optional profile override for every discovered artifact.",
)
def baseline(path: Path, output_path: Path | None, profile: str | None):
    """Record current found-control IDs without storing prompt text.

    Use the result with ``scan --baseline FILE --fail-on-regression``.  A
    baseline tracks controls present today; it does not establish a safety
    threshold and it never writes a prompt into the baseline file.
    """
    root = path.resolve()
    forced_profile = profile.lower() if profile else None
    entries = _baseline_entries(root, forced_profile)
    destination = output_path or root / ".crewscore-baseline.json"
    destination = destination.resolve()
    payload = baseline_payload(entries, ruleset=RULESET_ID)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    console.print(
        f"[green]Wrote prompt-free baseline:[/green] {destination} "
        f"({len(entries)} governed file(s), {sum(len(v['found_controls']) for v in payload['files'].values())} controls)."
    )
    console.print(
        "[dim]Use --fail-on-regression to protect written controls already present; "
        "add --require for an explicit policy.[/dim]"
    )


@main.command("init")
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--force",
    is_flag=True,
    help="Replace existing CrewScore configuration/template files in PATH.",
)
def init(path: Path, force: bool):
    """Create a prompt-free baseline and non-deploying GitHub workflow."""
    root = path.resolve()
    config_path = root / ".crewscore.yml"
    baseline_path = root / ".crewscore-baseline.json"
    workflow_path = root / ".github" / "workflows" / "crewscore.yml"
    targets = [config_path, baseline_path, workflow_path]
    existing = [target.relative_to(root) for target in targets if target.exists()]
    if existing and not force:
        err_console.print(
            "[red]Refusing to overwrite existing file(s):[/red] "
            + ", ".join(str(item) for item in existing)
        )
        err_console.print("[dim]Review them first, or re-run `crewscore init --force`.[/dim]")
        sys.exit(1)

    entries = _baseline_entries(root, None)
    baseline_path.write_text(
        json.dumps(baseline_payload(entries, ruleset=RULESET_ID), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    config_path.write_text(
        "# CrewScore policy: explicit controls and regressions, never a safety grade.\n"
        "version: 1\n"
        "baseline: .crewscore-baseline.json\n"
        "fail_on_regression: true\n"
        "required_controls: []\n"
        "# Add a dimension (for example human_gate) or a precise published control:\n"
        "# required_controls:\n"
        "#   - human_gate.approval_required\n"
        "#   - safe_stop.stop_condition\n"
        "forbid_missing: []\n",
        encoding="utf-8",
    )
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        "name: CrewScore\n\n"
        "on:\n"
        "  pull_request:\n"
        "  workflow_dispatch:\n\n"
        "permissions:\n"
        "  contents: read\n"
        "  # Sticky PR comment. Fork PRs still get a read-only token; the\n"
        "  # action degrades to a workflow warning instead of failing the job.\n"
        "  pull-requests: write\n\n"
        "jobs:\n"
        "  written-controls:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - name: Check written guardrails\n"
        "        uses: shmindmaster/crewscore@v2\n"
        "        with:\n"
        "          scan-path: .\n"
        "          config: .crewscore.yml\n"
        "          sarif: crewscore.sarif\n"
        "          pr-comment: 'true'\n"
        "      - name: Preserve SARIF findings\n"
        "        if: always()\n"
        "        uses: actions/upload-artifact@v4\n"
        "        with:\n"
        "          name: crewscore-sarif\n"
        "          path: crewscore.sarif\n"
        "          if-no-files-found: warn\n",
        encoding="utf-8",
    )
    console.print(f"[green]Created[/green] {config_path.relative_to(root)}")
    console.print(f"[green]Created[/green] {baseline_path.relative_to(root)}")
    console.print(f"[green]Created[/green] {workflow_path.relative_to(root)}")
    console.print(
        f"[dim]Baseline contains {len(entries)} governed artifact(s) and no prompt text. "
        "Edit .crewscore.yml to require controls explicitly.[/dim]"
    )


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
@click.option(
    "--include-inline/--no-inline",
    default=True,
    show_default=True,
    help=(
        "Also extract system_prompt / SYSTEM_PROMPT (etc.) string literals from "
        ".py/.ts/.js source so AI apps that bury prompts in code still get a "
        "coverage finding. Offline pattern match only."
    ),
)
@click.option(
    "--require",
    "required_controls",
    multiple=True,
    help="Require a public control ID or whole dimension (comma-separated; repeatable).",
)
@click.option(
    "--forbid-missing",
    "forbidden_missing_controls",
    multiple=True,
    help="Fail if a named public control ID or dimension is absent (repeatable).",
)
@click.option(
    "--baseline",
    type=click.Path(dir_okay=False),
    default=None,
    help="Prompt-free baseline JSON written by `crewscore baseline`.",
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    help="Fail only when a baseline control disappears.",
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Read required controls and baseline settings from .crewscore.yml.",
)
@click.option(
    "--sarif",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write prompt-free missing-control findings as SARIF 2.1.0.",
)
def scan(
    path,
    as_json,
    threshold,
    max_smells,
    explain,
    summary,
    profile,
    include_inline,
    required_controls,
    forbidden_missing_controls,
    baseline,
    fail_on_regression,
    config,
    sarif,
):
    """Discover and score agent prompt files under PATH (default: .).

    Looks for AGENTS.md, CLAUDE.md, system-prompt.md, files under
    agents/prompts/prompt directories, and (by default) system_prompt string
    literals embedded in .py/.ts/.js source. Offline structural scan only.
    """
    root = Path(path).resolve()
    policy = _resolve_policy_or_exit(
        config=config,
        require=required_controls,
        forbid_missing=forbidden_missing_controls,
        baseline=baseline,
        fail_on_regression=fail_on_regression,
    )
    oversized: list[Path] = []
    files = discover_prompt_files(root, oversized=oversized)
    inlines = discover_inline_prompt_sources(root) if include_inline else []
    if oversized and not as_json:
        for skipped in oversized:
            err_console.print(
                f"[yellow]Skipped {skipped} — larger than 500KB. "
                "Score it directly with crewscore test --prompt-file.[/yellow]"
            )

    if not files and not inlines:
        # Machine path: stdout must be valid JSON (same array shape as a
        # non-empty scan) so CI consumers never fail on json.loads. Human path
        # keeps the explanatory message. Exit stays non-zero either way so
        # empty repos fail closed.
        if as_json:
            click.echo("[]")
        else:
            err_console.print(
                f"[red]No agent prompt files found under {root}[/red]"
            )
            err_console.print(
                "[dim]Looking for AGENTS.md, CLAUDE.md, system-prompt.md, "
                "system_prompt.md, AGENT.md, prompts.md, files under "
                "agents/, prompts/, or prompt/ directories, and (default) "
                "system_prompt string literals in .py/.ts/.js source. "
                "Disable inline with --no-inline.[/dim]"
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

    # Inline literals: display path like src/a.py:SYSTEM_PROMPT; text lives on InlinePrompt.
    text_by_path: dict[str, str] = {}
    source_by_path: dict[str, str] = {}
    if inlines:
        inline_scored = score_inline_prompts(inlines, profile=forced_profile)
        for inl, item in zip(inlines, inline_scored):
            try:
                rel_file = str(Path(inl.path).resolve().relative_to(root))
            except ValueError:
                rel_file = str(inl.path)
            display = f"{rel_file}:{inl.name}"
            item["path"] = display
            text_by_path[display] = inl.text
            source_by_path[display] = f"{inl.path}:{inl.name}:L{inl.line}"
            scored.append(item)

    # Keep the established scan JSON rows and their numeric fields intact.
    # Policy evidence is an optional, control-only extension; SARIF gets the
    # same source-free findings without ever serializing prompt snippets.
    sarif_entries: list[tuple[str, bool, list[dict]]] = []
    scan_hero: dict | None = None
    scan_hero_matched = 10**9
    for item in scored:
        path_key = item["path"]
        if path_key in abs_by_rel:
            resolved_path = abs_by_rel[path_key]
            text = _read_prompt_file(resolved_path)
            source_for_policy = str(resolved_path)
        else:
            text = text_by_path.get(path_key, "")
            source_for_policy = source_by_path.get(path_key, path_key)

        _dimensions, findings = structural_analysis.analyze_with_findings(text)
        applicable = item.get("governance_applicable", True)
        if applicable:
            matched_n, total_n = coverage_from_findings(findings)
            hero = hero_missing_control(findings)
            item["coverage"] = {
                "matched": matched_n,
                "total": total_n,
                "missing": total_n - matched_n,
                "hero": hero,
            }
            # Prefer the hero from the lowest-coverage governed artifact.
            if hero is not None and matched_n < scan_hero_matched:
                scan_hero = hero
                scan_hero_matched = matched_n

        policy_result = _evaluate_policy_or_exit(
            policy,
            findings=findings,
            governance_applicable=applicable,
            source=source_for_policy,
            root=root,
        )
        if policy.enabled:
            item["policy"] = policy_result
        sarif_entries.append((item["path"], applicable, findings))
    if sarif:
        write_sarif(sarif, sarif_entries)

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
                f"[bold]{BRAND.upper()} — Written Control Coverage Scan[/bold]",
                border_style="blue",
                expand=False,
            )
        )
        console.print()
        n_inline = sum(1 for p in scored if p["path"] not in abs_by_rel)
        console.print(
            f"[dim]Scanned {root} — {len(scored)} artifact(s)"
            + (f" ({n_inline} inline source literal(s))" if n_inline else "")
            + ". Structural offline coverage only - not runtime proof.[/dim]"
        )
        console.print()

        any_smells = any(item.get("smells") for item in scored)
        any_config = any(not item.get("governance_applicable", True) for item in scored)
        any_coverage = any(item.get("coverage") for item in scored)

        table = Table(show_header=True, header_style="bold")
        table.add_column("Path", style="cyan", overflow="fold")
        table.add_column("Artifact")
        table.add_column("Coverage", justify="right")
        table.add_column("Verdict")
        if any_smells:
            table.add_column("Smells")

        for item in scored:
            governed = item.get("governance_applicable", True)
            color = tier_color(item["overall"]) if governed else "cyan"
            if governed and item.get("coverage"):
                cov = item["coverage"]
                cov_cell = (
                    f"[{color}]{cov['matched']}/{cov['total']}[/{color}]"
                )
            elif governed:
                cov_cell = f"[{color}]{item['overall']}/100[/{color}]"
            else:
                cov_cell = "[dim]n/a[/dim]"
            row = [
                item["path"],
                "prompt" if governed else "config",
                # Coverage N/23 for prompts; config never gets a governance grade.
                cov_cell,
                f"[{color}]{item['tier']}[/{color}]",
            ]
            if any_smells:
                names = [s["name"] for s in item.get("smells", [])]
                row.append(f"[yellow]{', '.join(names)}[/yellow]" if names else "")
            table.add_row(*row)

        console.print(table)
        console.print()

        if scan_hero:
            console.print(
                f"  [bold red]FIRST GAP TO REVIEW:[/bold red] {scan_hero.get('label')}"
            )
            if scan_hero.get("concept"):
                console.print(
                    f"  [dim]Gate CI on it: [bold]crewscore scan . "
                    f"--require {scan_hero['concept']}[/bold][/dim]"
                )
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
        if any_coverage:
            console.print(
                "  [dim]Coverage = written controls present / 23 published. "
                "Not a quality ranking or runtime safety proof.[/dim]"
            )
        if any_config or any_smells or any_coverage:
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
            # Failure reasons always reach stderr, including --json runs: an
            # exit code 2 with a silent log is the single most common reason
            # a CI gate gets deleted instead of fixed. stdout stays pure JSON.
            for item in below:
                err_console.print(
                    f"  [red]Threshold failure: {item['path']} "
                    f"{item['overall']} < {threshold}[/red]"
                )

    if max_smells is not None:
        over = [item for item in scored if len(item.get("smells", [])) > max_smells]
        if over:
            failed = True
            for item in over:
                err_console.print(
                    f"  [red]Smell threshold failure: {item['path']} "
                    f"{len(item['smells'])} > {max_smells}[/red]"
                )

    policy_failures = [
        item for item in scored if item.get("policy", {}).get("failed")
    ]
    if policy_failures:
        failed = True
        for item in policy_failures:
            details = item["policy"]
            missing = details.get("missing_required_controls") or []
            regressions = details.get("regressed_controls") or []
            if missing:
                err_console.print(
                    f"  [red]Required-control failure: {item['path']} "
                    f"missing {', '.join(missing)}[/red]"
                )
            if regressions:
                err_console.print(
                    f"  [red]Regression failure: {item['path']} "
                    f"lost {', '.join(regressions)}[/red]"
                )
    elif not as_json:
        gated = sorted(
            {
                control
                for item in scored
                for control in item.get("policy", {}).get("required_controls") or []
            }
        )
        if gated:
            err_console.print(
                f"  [green]Required controls present:[/green] {', '.join(gated)}"
            )

    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()

