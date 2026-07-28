"""HTML report, SVG badge, and share text for CrewScore."""

from xml.etree import ElementTree

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.profiles import CODING_AGENT_CONFIG
from crewscore.report import render_badge_svg, render_html_report, share_text
from crewscore.scoring import build_result

_ZERO_DIMS = {
    k: 0
    for k in [
        "injection",
        "hallucination",
        "citation",
        "cost",
        "human_gate",
        "safe_stop",
        "audit",
        "compliance",
    ]
}


def _result(overall_dims=None):
    dims = overall_dims or dict(_ZERO_DIMS)
    return build_result(dims, mode="structural", source="prompt")


def _smell(name="Context Bloat", smell_id="smell.context_bloat"):
    return {
        "smell_id": smell_id,
        "name": name,
        "detail": "251 lines (>= 200)",
        "heuristic": ">= 200 lines",
        "paper_prevalence": "42% of 100 popular OSS projects",
        "citation": "dos Santos et al., arXiv:2606.15828",
        "deterministic": True,
        "approximates_paper": False,
        "affects_score": False,
    }


def _config_result(smells=None):
    """A coding-agent config result — governance dimensions do not apply."""
    return build_result(
        dict(_ZERO_DIMS),
        mode="structural",
        source="AGENTS.md",
        smells=smells or [],
        profile=CODING_AGENT_CONFIG,
    )


def test_html_contains_score_and_disclaimer():
    html = render_html_report(_result())
    assert "0/100" in html
    assert "Structural" in html or "structural" in html or "hygiene" in html.lower()
    assert "crewscore.ai" in html
    assert "black box" in html.lower() or "ruleset" in html.lower()
    assert "<script" not in html.lower()  # no external/runtime scripts required
    # Self-contained: inline CSS present, no external stylesheet link
    assert "<style" in html.lower()
    assert 'rel="stylesheet"' not in html.lower()
    assert "http://" not in html  # no insecure external assets


def test_html_findings_include_rule_ids():
    findings = [
        {
            "dimension": "injection",
            "status": "missing",
            "pattern_or_reason": "Reject override attempts",
            "snippet": None,
            "rule_id": "injection.01",
        }
    ]
    html = render_html_report(_result(), findings=findings)
    assert "injection.01" in html
    assert "Open findings" in html


def test_html_has_inline_css_and_dimensions():
    html = render_html_report(
        _result(
            {
                "injection": 40,
                "hallucination": 0,
                "citation": 0,
                "cost": 0,
                "human_gate": 0,
                "safe_stop": 0,
                "audit": 0,
                "compliance": 0,
            }
        )
    )
    assert "<style" in html
    assert "Prompt Injection" in html or "injection" in html.lower()


def test_badge_svg_contains_score():
    svg = render_badge_svg(_result())
    assert "svg" in svg.lower()
    assert "CrewScore" in svg
    assert "0/100" in svg


def test_share_text_includes_score_and_url():
    text = share_text(_result())
    assert "0/100" in text
    assert "crewscore.ai" in text


def test_badge_for_config_shows_smell_verdict_not_a_grade():
    """A build-instructions file must never wear a 0/100 badge."""
    svg = render_badge_svg(_config_result([_smell(), _smell("Lint Leakage", "smell.lint_leakage")]))
    assert "/100" not in svg
    assert "config: 2 smells" in svg
    root = ElementTree.fromstring(svg)  # well-formed
    # Badge must be wide enough for the longer config text, not the 54px
    # value box sized for "0/100".
    assert int(root.get("width")) >= 78 + 7 * len("config: 2 smells")


def test_badge_for_clean_config_says_clean_and_is_green():
    svg = render_badge_svg(_config_result([]))
    assert "config: clean" in svg
    assert "/100" not in svg
    assert "#10b981" in svg  # green — no smells found


def test_badge_for_config_singular_smell():
    svg = render_badge_svg(_config_result([_smell()]))
    assert "config: 1 smell" in svg
    assert "smells" not in svg


def test_html_for_config_shows_smells_not_governance_bars():
    html = render_html_report(_config_result([_smell()]))
    assert "0/100" not in html
    assert "CONFIG: 1 SMELL" in html
    assert "Context Bloat" in html
    assert "dim-row" not in html
    assert "Prompt Injection" not in html
    # The governance formula does not describe how this file was judged.
    assert "15+85" not in html
    assert "configuration smell" in html.lower()
    assert "arxiv" in html.lower()


def test_html_for_clean_config_says_no_smells():
    html = render_html_report(_config_result([]))
    assert "CONFIG: NO SMELLS DETECTED" in html
    assert "/100" not in html
    assert "no configuration smells" in html.lower()


def test_cli_config_file_badge_and_report_carry_no_grade(tmp_path):
    """cli test --prompt-file AGENTS.md writes both artifacts; neither grades."""
    config = tmp_path / "AGENTS.md"
    config.write_text("# Build\n\nRun `make test`.\n", encoding="utf-8")
    report = tmp_path / "out.html"
    badge = tmp_path / "badge.svg"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "test",
            "--prompt-file",
            str(config),
            "--report",
            str(report),
            "--badge",
            str(badge),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "/100" not in badge.read_text(encoding="utf-8")
    assert "0/100" not in report.read_text(encoding="utf-8")


def test_cli_writes_report_and_badge(tmp_path):
    runner = CliRunner()
    report = tmp_path / "out.html"
    badge = tmp_path / "badge.svg"
    result = runner.invoke(
        main,
        [
            "test",
            "--prompt",
            "You are helpful.",
            "--report",
            str(report),
            "--badge",
            str(badge),
            "--json",
        ],
    )
    assert result.exit_code == 0
    assert report.exists()
    assert "CrewScore" in report.read_text(encoding="utf-8")
    assert badge.exists()
    assert "svg" in badge.read_text(encoding="utf-8").lower()


def test_cli_report_and_badge_create_parent_dirs(tmp_path):
    runner = CliRunner()
    report = tmp_path / "nested" / "out" / "report.html"
    badge = tmp_path / "nested" / "out" / "badge.svg"
    result = runner.invoke(
        main,
        [
            "test",
            "--prompt",
            "You are helpful.",
            "--report",
            str(report),
            "--badge",
            str(badge),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert report.exists()
    assert badge.exists()
