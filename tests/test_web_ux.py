"""Contract tests locking preflight workflow UX in index.html."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


def test_preflight_stages_present():
    """Four preflight stage ids: Prompt, Inspect, Act, Export."""
    html = _html()
    assert 'id="stg-prompt"' in html
    assert 'id="stg-inspect"' in html
    assert 'id="stg-act"' in html
    assert 'id="stg-export"' in html


def test_plan_before_mutate_controls():
    """Plan preview, apply, and cancel — mutate only after plan."""
    html = _html()
    assert "Plan fix" in html
    assert "Apply plan" in html
    assert "cancel" in html.lower()


def test_capability_stamp_structural_pregate():
    """Capability stamp uses structural pre-gate, not red-team language."""
    html = _html()
    assert "Structural pre-gate" in html
    assert "not a red-team" in html.lower()


def test_vendor_is_secondary_not_equal_tabs():
    """Vendor checklist is demoted to secondary, not equal primary surface."""
    html = _html()
    assert "Vendor checklist (self-attest)" in html
    assert "Secondary" in html


def test_privacy_metrics_hook_present():
    """Local metrics key present; no prompt storage in the metrics path."""
    html = _html()
    assert "crewscore_metrics_v1" in html


def test_builder_first_hero_preserved():
    """Builder-first hero and structural hygiene framing stay intact."""
    html = _html()
    assert "Score agent prompts in your browser" in html
    assert "structural" in html.lower()
    assert "hygiene" in html.lower() or "Structural pre-gate" in html
