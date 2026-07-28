"""Vendor scorecard polish: red flags and pure result builder."""

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


def test_json_includes_red_flags():
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


def test_index_html_share_uses_data_attrs_not_json_onclick():
    """Vendor share must not inject JSON.stringify into double-quoted onclick."""
    text = Path("index.html").read_text(encoding="utf-8")
    assert "JSON.stringify(opts.shareExtra)" not in text
    assert "data-share" in text
    assert "addEventListener" in text


def test_index_html_onpage_flags_use_shared_vendor_logic():
    """On-page RED FLAG list must use same NO + critical-DK logic as share."""
    text = Path("index.html").read_text(encoding="utf-8")
    # Display path must prefer opts.flags (shared with shareExtra) over score===0 only
    assert "opts.flags" in text
    # Critical indices for certification, audit, human_override, security_audit, incident
    assert "VENDOR_CRITICAL" in text
