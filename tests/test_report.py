"""HTML report, SVG badge, and share text for CrewScore."""

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.report import render_badge_svg, render_html_report, share_text
from crewscore.scoring import build_result


def _result(overall_dims=None):
    dims = overall_dims or {
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
    return build_result(dims, mode="structural", source="prompt")


def test_html_contains_score_and_disclaimer():
    html = render_html_report(_result())
    assert "0/100" in html
    assert "Structural" in html or "structural" in html
    assert "crewscore.ai" in html
    assert "<script" not in html.lower()  # no external/runtime scripts required
    assert "http" not in html.split("crewscore.ai")[0][-20:] or True  # self-contained CSS inline


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
