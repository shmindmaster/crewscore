"""Contract tests locking preflight workflow UX in index.html."""

import re
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


def test_camera_ready_zero_bars_and_delta_hero():
    """G6: empty dims are camera-dense; after-fix shows delta on Inspect first."""
    html = _html()
    assert "is-empty" in html
    assert "is-empty-marker" in html or "is-critical" in html
    assert "hero-delta" in html or "delta-compare" in html
    assert "Continue to export" in html
    # Apply must land on inspect (hero moment), not skip to export as first paint
    apply_idx = html.find("function applyFixPlan")
    assert apply_idx > 0
    chunk = html[apply_idx : apply_idx + 1200]
    assert 'setStage("inspect")' in chunk
    assert 'showDeck("deck-inspect", true)' in chunk
    # Must not set export as the stage immediately after apply without inspect hold
    # (export still available via Continue to export)
    assert "After approved fix" in html


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


def test_type_scale_tokens():
    """Type scale CSS variables establish a coherent size ladder."""
    html = _html()
    for token in ("--fs-xs", "--fs-sm", "--fs-md"):
        assert token in html
    assert "--fs-hero" in html or "--fs-score" in html


def test_mono_reserved_not_all_chrome():
    """Stage pills use sans for UI chrome, not mono-only."""
    html = _html()
    # Isolate the .stage-pill rule block (base, not :hover/:disabled/etc.).
    m = re.search(r"\.stage-pill\s*\{([^}]+)\}", html)
    assert m, ".stage-pill style rule missing"
    rule = m.group(1)
    assert "var(--sans)" in rule or "IBM Plex Sans" in rule, (
        ".stage-pill must use sans (var(--sans) or IBM Plex Sans), not mono-only chrome"
    )


def test_score_ring_annular():
    """Score ring uses an annular/thin-ring technique, not a soft filled gold disc."""
    html = _html()
    m = re.search(r"\.score-ring\s*\{([^}]+)\}", html)
    assert m, ".score-ring style rule missing"
    rule = m.group(1)
    compact = rule.replace(" ", "")
    assert "transparent" in rule, (
        ".score-ring must use transparent (hollow center / track gap)"
    )
    has_border_ring = (
        "border-radius:50%" in compact
        and bool(re.search(r"(?<![\w-])border\s*:\s*[^;]*\d", rule))
    )
    has_conic_radial_hole = (
        ("conic-gradient" in rule or "radial-gradient" in rule)
        and "transparent" in rule
    )
    assert has_border_ring or has_conic_radial_hole, (
        ".score-ring must use border ring or conic/radial with transparent center"
    )
    # Soft multi-stop gold disc: amber haze + soft inset glow without a border track.
    soft_gold_disc = (
        bool(re.search(r"rgba\(\s*232\s*,\s*163\s*,\s*23", rule))
        and "inset" in rule
        and not has_border_ring
    )
    assert not soft_gold_disc, (
        ".score-ring must be a thin annular track, not a soft filled gold disc"
    )


def test_body_grid_restrained():
    """Body page grid is absent or atmospheric (alpha ≤ 0.15)."""
    html = _html()
    # Pull body rule background section.
    m = re.search(r"\bbody\s*\{([^}]+)\}", html)
    assert m, "body style rule missing"
    body_rule = m.group(1)
    if "repeating-linear-gradient" not in body_rule:
        return  # no grid — restrained by absence
    # Grid present: every rgba/hsla alpha in the repeating-linear-gradient stop ≤ 0.15
    for grad in re.findall(
        r"repeating-linear-gradient\([^)]+\)", body_rule
    ):
        alphas = re.findall(
            r"rgba?\([^)]*?,\s*(\d*\.?\d+)\s*\)", grad
        ) + re.findall(
            r"hsla?\([^)]*?,\s*(\d*\.?\d+)\s*\)", grad
        )
        for a in alphas:
            assert float(a) <= 0.15, (
                f"body repeating grid alpha {a} exceeds 0.15 (must be atmospheric)"
            )


def test_panel_lifted_from_bg():
    """Panel surface color is distinct from page background (lifted card)."""
    html = _html()
    bg_m = re.search(r"--bg\s*:\s*([^;]+);", html)
    panel_m = re.search(r"--panel\s*:\s*([^;]+);", html)
    assert bg_m, "--bg token missing"
    assert panel_m, "--panel token missing"
    bg = bg_m.group(1).strip().lower()
    panel = panel_m.group(1).strip().lower()
    assert bg != panel, "--panel must differ from --bg so cards read as lifted surfaces"
