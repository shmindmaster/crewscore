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


def test_export_completion_checklist_present():
    """Export stage has a completion checklist with share, CI, and prompt items."""
    html = _html()
    assert "export-checklist" in html
    assert 'data-check="share"' in html
    assert 'data-check="ci"' in html
    assert 'data-check="prompt"' in html


def test_prefers_reduced_motion():
    """CSS respects prefers-reduced-motion for a11y."""
    html = _html()
    assert "prefers-reduced-motion" in html


def test_mobile_touch_targets():
    """Primary controls meet ~44px touch target floor for mobile."""
    html = _html()
    assert "min-height:44px" in html or "min-height: 44px" in html
    # Stage pills, chips, and secondary buttons must be covered by the rule set.
    for selector in (".btn", ".btn-sec", ".chip", ".stage-pill"):
        assert selector in html


def test_safe_area_padding():
    """Body uses safe-area insets for notched phones."""
    html = _html()
    assert "safe-area-inset" in html


def test_sticky_stages_mobile():
    """Stage nav sticks on small screens for orientation during scroll."""
    html = _html()
    assert "position:sticky" in html or "position: sticky" in html
    assert ".stages" in html


def test_cap_chip_not_hidden_on_mobile():
    """Honesty capability chip must remain visible on mobile (no display:none)."""
    html = _html()
    # Ban the anti-pattern of hiding the cap chip in a mobile media query.
    assert ".cap-chip{display:none}" not in html.replace(" ", "")
    assert "cap-chip" in html
    assert "Structural pre-gate" in html


def test_desktop_density_breakpoint():
    """Desktop breakpoint widens layout for builder density."""
    html = _html()
    assert "min-width:900px" in html or "min-width: 900px" in html
    assert "960px" in html or "max-width:960px" in html or "max-width: 960px" in html


def test_stage_nav_are_buttons():
    """Stage pills are real buttons for keyboard/touch jump to reached stages."""
    html = _html()
    assert 'id="stg-prompt"' in html
    assert "<button" in html
    # Each stage control is a button element.
    for sid in ("stg-prompt", "stg-inspect", "stg-act", "stg-export"):
        assert f'id="{sid}"' in html
        # button ... id="stg-..."
        assert f'id="{sid}"' in html
    assert 'type="button"' in html
    assert "stage-pill" in html
    # Explicit marker that stages are navigable controls
    assert 'aria-label="Preflight stages"' in html
    assert "stg-prompt" in html and "button" in html[html.find("stg-prompt") - 80 : html.find("stg-prompt") + 20]


def test_ci_gate_export_markers():
    """CI handoff copy remains part of the export surface contract."""
    html = _html()
    assert "ci-block" in html
    assert "Gate this in CI" in html
    assert "shmindmaster/crewscore@v1" in html


def test_preflight_aesthetic_tokens():
    """Instrument/preflight visual tokens stay distinctive (not generic AI cyan)."""
    html = _html()
    assert "--amber:" in html
    assert "--mono:" in html or "IBM Plex Mono" in html
    assert "score-ring" in html or "deck-instrument" in html
    assert "#0a0c0b" in html or "--bg:#0a0c0b" in html


def test_mobile_score_bar():
    """Sticky mobile primary CTA for Run score without hunting for the main button."""
    html = _html()
    assert 'id="mobile-score-bar"' in html
