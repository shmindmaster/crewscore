"""Vendor checklist: self-attested response summaries, never verdicts."""

from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.vendor_scorecard import build_vendor_result


def test_red_flags_list_for_nos():
    payload = build_vendor_result("Acme", "n,n,n,n,n,n,n,n,n,n")
    assert payload["score"] == 0
    assert len(payload["red_flags"]) >= 3
    assert all(isinstance(x, str) for x in payload["red_flags"])


def test_mixed_answers_red_flags_only_nos_or_critical_dk():
    payload = build_vendor_result("Acme", "y,y,n,dk,y,y,n,y,n,y")
    assert payload["red_flags"]
    # certification NO, audit DK (critical), pricing NO, production_refs NO
    flags_joined = " ".join(payload["red_flags"]).lower()
    assert "certif" in flags_joined or "soc2" in flags_joined or "hipaa" in flags_joined
    assert "audit" in flags_joined
    # Explicit expected set: cert NO, audit DK, pricing NO, production_refs NO
    assert len(payload["red_flags"]) == 4
    # Non-critical DK alone must not produce a red flag
    soft = build_vendor_result("Soft", "y,dk,y,y,y,y,y,y,y,y")  # benchmark DK only
    assert soft["red_flags"] == []


def test_json_includes_red_flags_and_stable_schema():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "assess-vendor",
            "--name",
            "Acme AI",
            "--answers",
            "n,n,n,n,n,n,n,n,n,n",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    import json

    payload = json.loads(result.output)
    assert "red_flags" in payload
    assert len(payload["red_flags"]) >= 3
    assert payload["self_attested"] is True
    assert payload["not_independent_audit"] is True
    assert payload["not_vendor_safety_grade"] is True
    assert payload["schema_version"]
    assert payload["question_count"] == 10
    assert "next_crewscore_checks" in payload
    # Gaps should map to at least one real follow-up with published control IDs.
    assert payload["next_crewscore_checks"]
    for item in payload["next_crewscore_checks"]:
        assert "from_question_key" in item
        assert "suggested_cli" in item
        assert item["suggested_cli"].startswith("crewscore")
    # Answer rows carry theme metadata for machine consumers.
    assert all("crewscore_dimensions" in a for a in payload["answers"])
    assert all("key" in a for a in payload["answers"])


def test_assess_vendor_report_writes_html(tmp_path: Path):
    report = tmp_path / "vendor.html"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "assess-vendor",
            "--name",
            "Acme AI",
            "--answers",
            "y,y,n,dk,y,y,n,y,n,y",
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == 0, result.output
    assert report.exists()
    html = report.read_text(encoding="utf-8")
    assert "Acme AI" in html
    assert "crewscore" in html.lower()
    assert "not an independent audit, certification, or vendor verdict" in html
    assert "Suggested CrewScore follow-ups" in html or "crewscore" in html.lower()


def test_next_crewscore_checks_use_published_control_ids():
    from crewscore.scorers.structural_analysis import CONCEPTS
    from crewscore.vendor_scorecard import build_vendor_result

    published = {c.key for concepts in CONCEPTS.values() for c in concepts}
    payload = build_vendor_result("Acme", "n,n,n,n,n,n,n,n,n,n")
    for item in payload["next_crewscore_checks"]:
        for control in item.get("controls") or []:
            assert control in published, f"unknown control id: {control}"


def test_index_html_share_uses_data_attrs_not_json_onclick():
    """Vendor share must not inject JSON.stringify into double-quoted onclick."""
    text = Path("assets/site.js").read_text(encoding="utf-8")
    assert "JSON.stringify(opts.shareExtra)" not in text
    assert "addEventListener" in text
    assert "data-social" in text


def test_index_html_uses_shared_engine_for_vendor_and_agent():
    """Web must load generated score-engine.js (Python parity), not a private dual scorer."""
    text = Path("assets/site.js").read_text(encoding="utf-8")
    vendor = Path("assets/vendor.js").read_text(encoding="utf-8")
    assert 'src="score-engine.js"' in Path("index.html").read_text(encoding="utf-8")
    assert "CrewScoreEngine" in text
    assert "analyzeArtifact" in text
    assert "CrewScoreEngine" in vendor


def test_index_html_escapes_user_titles_before_innerhtml():
    """Vendor/agent titles and flags must be HTML-escaped before innerHTML."""
    text = Path("assets/vendor.js").read_text(encoding="utf-8")
    assert "const esc" in text
    assert "esc($(\"vendor-name\")" in text
    assert "esc(question)" in text


def test_browser_vendor_checklist_has_no_score_or_verdict_engine():
    """The browser summarizes responses; it does not score or grade a vendor."""
    text = Path("assets/vendor.js").read_text(encoding="utf-8")
    assert "not a vendor grade" in text
    engine = Path("score-engine.js").read_text(encoding="utf-8")
    assert "scoreVendor" not in engine
    assert "vendorTier" not in engine
    assert "TRUSTED" not in engine


def test_index_html_hero_is_builder_first():
    """Hero sells prompt scoring to builders, not a vendor quiz, and is honest.

    This used to pin the exact headline, so every copy edit broke it and told
    us nothing. What must hold is the positioning: the hero is about scoring
    your own prompt, and it states the coverage-not-quality limit up front
    rather than burying it in docs/validation.md.
    """
    text = Path("index.html").read_text(encoding="utf-8")
    hero = text.split('<section class="hero"', 1)[1].split("</section>", 1)[0]
    lowered = hero.lower()

    # Builder-first: the subject is the reader's own prompt.
    assert "prompt" in lowered
    # Not the vendor-procurement quiz, which is the secondary path.
    assert "buying ai software" not in lowered

    # The limit is stated in the hero, not only in the study.
    assert "written-control coverage" in lowered
    assert "runtime proof" in lowered


def test_index_html_vendor_tab_is_secondary_self_attest():
    """Vendor path is demoted: self-attest checklist, not equal hero chrome."""
    text = Path("index.html").read_text(encoding="utf-8")
    assert 'href="vendor-checklist/"' in text
    # Must not be equal-weight primary tab chrome
    assert "vendor-questions" not in text
    # Old equal-weight buyer framing should not remain as the tab label
    assert "I’m buying AI software" not in text
    assert "I'm buying AI software" not in text


def test_index_html_authenticity_line_warns_templates_and_not_red_team():
    """Short authenticity: structural text scan, not red-team; templates can inflate."""
    text = Path("assets/site.js").read_text(encoding="utf-8").lower()
    assert "runtime proof" in text
    assert "editable text suggestions" in Path("index.html").read_text(encoding="utf-8").lower()


def test_vendor_get_tier_thresholds():
    """Checklist labels describe response follow-up, never vendor quality."""
    from crewscore.vendor_scorecard import get_tier

    assert get_tier(100)[0] == "MOSTLY POSITIVE RESPONSES"
    assert get_tier(80)[0] == "MOSTLY POSITIVE RESPONSES"
    assert get_tier(79)[0] == "FOLLOW-UP NEEDED"
    assert get_tier(50)[0] == "FOLLOW-UP NEEDED"
    assert get_tier(49)[0] == "MATERIAL GAPS"
    assert get_tier(30)[0] == "MATERIAL GAPS"
    assert get_tier(29)[0] == "INSUFFICIENT EVIDENCE"
    assert get_tier(0)[0] == "INSUFFICIENT EVIDENCE"


def test_assess_vendor_report_creates_parent_dirs(tmp_path: Path):
    report = tmp_path / "nested" / "out" / "vendor.html"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "assess-vendor",
            "--name",
            "Acme AI",
            "--answers",
            "y,y,n,dk,y,y,n,y,n,y",
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == 0, result.output
    assert report.exists()
    assert "Acme AI" in report.read_text(encoding="utf-8")
