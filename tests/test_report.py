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
    assert "Control coverage" in text
    assert "not runtime proof" in text


def test_share_text_does_not_claim_production_readiness():
    """share_text is the one string users post in public.

    docs/validation.md retracts the production-readiness claim: at equal
    length the score does not separate production-labeled prompts from amateur ones.
    Shipping the retracted wording on the most-quoted surface in the product
    is how the old claim outlives the correction.
    """
    lowered = share_text(_result()).lower()
    assert "production-readiness" not in lowered
    assert "production readiness" not in lowered
    # Coverage language, not vanity quality ranking.
    assert "control coverage" in lowered
    assert "my ai agent scored" not in lowered


def _badge_geometry(svg: str) -> dict:
    """svg width, the two panel rects, and the value text with its anchor."""
    root = ElementTree.fromstring(svg)  # also asserts well-formedness
    rects = [r for r in root.iter("{http://www.w3.org/2000/svg}rect")]
    texts = [t for t in root.iter("{http://www.w3.org/2000/svg}text")]
    value_rect = next(r for r in rects if r.get("x"))
    return {
        "width": float(root.get("width")),
        "label_w": float(value_rect.get("x")),
        "value_w": float(value_rect.get("width")),
        "value_text": texts[-1].text,
        "value_x": float(texts[-1].get("x")),
    }


def test_badge_for_config_shows_smell_verdict_not_a_grade():
    """A build-instructions file must never wear a 0/100 badge."""
    svg = render_badge_svg(_config_result([_smell(), _smell("Lint Leakage", "smell.lint_leakage")]))
    assert "/100" not in svg
    assert "config: 2 smells" in svg


def test_badge_panels_fit_their_text_and_tile_the_svg():
    """The value text must sit centered inside its own colored panel.

    Reusing the governed badge's fixed value box for the longer config string
    pushes the text out of its panel and past the right edge of the SVG.
    """
    for result in (
        _result(),
        _config_result([]),
        _config_result([_smell()] * 12),
    ):
        g = _badge_geometry(render_badge_svg(result))
        # Panels tile the badge exactly — no gap, no overflow.
        assert g["label_w"] + g["value_w"] == g["width"]
        # Text is centered in the value panel and stays inside it.
        assert g["value_x"] == g["label_w"] + g["value_w"] / 2
        half_text = 3.5 * len(g["value_text"])  # conservative glyph half-width
        assert g["value_x"] - half_text > g["label_w"]
        assert g["value_x"] + half_text < g["width"]


def test_badge_grows_with_longer_verdict_text():
    narrow = _badge_geometry(render_badge_svg(_config_result([])))
    wide = _badge_geometry(render_badge_svg(_config_result([_smell()] * 12)))
    assert len(wide["value_text"]) > len(narrow["value_text"])
    assert wide["value_w"] > narrow["value_w"]


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


_LEAK_MARKER = "LEAK-MARKER-injection.01"


def _leaky_findings():
    """Governance findings, as `test --explain` would produce them."""
    return [
        {
            "dimension": "injection",
            "status": "missing",
            "rule_id": _LEAK_MARKER,
            "pattern_or_reason": "Reject override attempts",
        }
    ]


def test_html_report_for_config_ignores_governance_findings():
    """Config takes the smell scorecard, so findings must not reach the page.

    The config branch happens not to read `findings` today. That is structure,
    not a guarantee: nothing stopped a later edit from threading them through
    and quietly putting a governance grade back on an AGENTS.md report. This
    pins the behavior instead of the current shape.
    """
    html = render_html_report(_config_result(), findings=_leaky_findings())
    assert _LEAK_MARKER not in html
    assert "/100" not in html
    assert "15+85" not in html and "15 + 85" not in html
