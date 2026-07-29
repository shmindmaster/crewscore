"""Fast contracts for the controls-first static site.

Playwright owns interaction coverage.  These tests deliberately verify only
non-negotiable public copy and asset boundaries that should fail before a
browser is started.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


def test_controls_first_workspace_replaces_the_wizard_and_score_tier():
    html = _html()
    assert "Find the safety rules your AI agent prompt forgot." in html
    assert "Try a 10-second demo" in html
    assert "Check my instructions" in html
    assert 'id="checker-workspace"' in html
    assert 'id="mode-toggle"' in html
    assert 'id="stg-prompt"' not in html
    assert "score-ring" not in html
    assert "STRUCTURAL: CRITICAL GAPS" not in html


def test_primary_input_supports_paste_upload_and_public_github():
    html = _html()
    assert 'id="agent-prompt"' in html
    assert 'id="prompt-file"' in html
    assert 'id="drop-zone"' in html
    assert 'id="prompt-url"' in html
    assert "github.com" in html
    assert "raw.githubusercontent.com" in html


def test_imports_validate_utf8_and_offer_a_recovery_path():
    script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    assert 'TextDecoder("utf-8", { fatal: true })' in script
    assert "not valid UTF-8 text" in script
    assert "Save it as UTF-8" in script


def test_privacy_contract_has_no_remote_font_and_offers_opt_out():
    html = _html()
    assert "fonts.googleapis.com" not in html
    assert "Your prompt text never leaves your browser" in html
    assert 'id="analytics-opt-out"' in html
    assert 'href="privacy.html"' in html
    assert 'href="security.html"' in html


def test_vendor_is_a_separate_secondary_page():
    html = _html()
    assert 'href="vendor-checklist/"' in html
    assert "vendor-questions" not in html
    assert (ROOT / "vendor-checklist" / "index.html").exists()


def test_static_site_uses_local_shared_assets_and_generated_engine():
    html = _html()
    assert 'href="assets/site.css"' in html
    assert 'src="score-engine.js"' in html
    assert 'src="assets/site.js"' in html
    assert (ROOT / "assets" / "site.css").exists()
    assert (ROOT / "assets" / "site.js").exists()


def test_result_and_share_contracts_are_present_without_prompt_export():
    html = _html()
    assert 'id="results"' in html
    script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    assert "written guardrails found" in script
    assert "#cs-result=" in script
    assert "navigator.share" in script
    assert "Copy for Slack/Teams" in script
    assert "Download Facebook SVG" in script
    assert "JSON findings" in script
    assert "prompt text is never included" in script.lower()


def test_copy_fallback_is_not_held_by_a_stuck_browser_clipboard_api():
    script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    assert "writeClipboardWithFallbackTimeout" in script
    assert "Clipboard write timed out." in script
    assert "await writeClipboardWithFallbackTimeout(value)" in script
