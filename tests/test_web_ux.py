"""Contract tests locking the public positioning copy.

Two surfaces, one claim: index.html (the preflight workflow a visitor sees)
and README.md (the first thing a reader sees on GitHub). Both must say the
number is *coverage*, not a quality ranking, and both must carry the
validation study that proves it.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The site is served at crewscore.ai, where docs/ does not exist — the study
# has to be linked at its canonical GitHub URL or the link is dead in prod.
VALIDATION_URL = (
    "https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md"
)


def _html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_preflight_stages_present():
    """Wizard-lite: three stages — Prompt, Score, Export (plan is a sheet)."""
    html = _html()
    assert 'id="stg-prompt"' in html
    assert 'id="stg-inspect"' in html
    assert 'id="stg-export"' in html
    assert 'id="stg-act"' not in html
    assert ">2 Coverage<" in html


def test_plan_before_mutate_controls():
    """Plan preview, apply, and cancel — mutate only after plan."""
    html = _html()
    assert "Plan fix" in html
    assert "Apply plan" in html
    assert "cancel" in html.lower()


def test_config_verdict_never_prints_a_slash_100_number():
    """Config verdict explanatory prose cites corpus rationale, not a grade
    for the user's file — it must never render an N/100 number, since it
    sits directly beneath a config verdict a screenshot would misread as
    the user's own score."""
    html = _html()
    match = re.search(
        r"function renderConfigVerdict\(result\) \{.*?\n  \}", html, re.S
    )
    assert match, "renderConfigVerdict function not found"
    body = match.group(0)
    assert not re.search(r"\d+/100", body)


def test_wizard_lite_sheets_over_score():
    """Plan and export are sheets; score deck stays the mounted product surface."""
    html = _html()
    assert 'id="sheet-plan"' in html
    assert 'id="sheet-export"' in html
    assert 'id="sheet-backdrop"' in html
    assert 'id="deck-inspect"' in html
    assert 'id="deck-act"' not in html
    assert 'id="deck-export"' not in html
    assert "openSheet" in html
    assert "closeSheets" in html
    # Apply closes sheet and re-renders score in place
    apply_idx = html.find("function applyFixPlan")
    chunk = html[apply_idx : apply_idx + 1400]
    assert "closeSheets()" in chunk
    assert 'setStage("inspect")' in chunk


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
    """Builder-first hero stays: browser-local, no signup, structural framing.

    The headline moved from "Score agent prompts in your browser" to a
    coverage claim, but the builder-first promises around it must survive
    the reframe rather than be lost with it.
    """
    html = _html()
    assert "in your browser" in html
    assert "no signup" in html.lower()
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
    for sid in ("stg-prompt", "stg-inspect", "stg-export"):
        assert f'id="{sid}"' in html
    assert 'type="button"' in html
    assert "stage-pill" in html
    assert 'aria-label="Preflight stages"' in html
    assert "stg-prompt" in html and "button" in html[html.find("stg-prompt") - 80 : html.find("stg-prompt") + 20]


def test_ci_gate_export_markers():
    """CI handoff copy remains part of the export surface contract."""
    html = _html()
    assert "ci-block" in html
    assert "Gate this in CI" in html
    assert "shmindmaster/crewscore@v1" in html


def test_config_ci_snippet_does_not_pin_partial_browser_smell_count():
    """The config-mode CI snippet must not gate on the browser's partial smell
    count. Only 1 of 3 detectors runs in-browser (Init Fossilization and Lint
    Leakage need git history / repo access the browser doesn't have) — if the
    copy-paste snippet bakes in `smells.length` from that partial scan, a
    visitor who copies it without reading gets a CI gate pinned to a count
    the full CLI will immediately exceed, red-building the very file the
    site just called clean. The snippet must use a fixed, scan-independent
    default and must carry its own disclosure so a reader who copies the
    snippet out of the page is not misled by the snippet text alone."""
    html = _html()
    match = re.search(r"function renderConfigExport\(\) \{.*?\n  \}", html, re.S)
    assert match, "renderConfigExport function not found"
    body = match.group(0)
    ci_match = re.search(r"const ci = `([\s\S]*?)`;", body)
    assert ci_match, "ci template literal not found in renderConfigExport"
    ci = ci_match.group(1)
    # No interpolation of the browser's partial smell count into the gate.
    assert "smells.length" not in ci
    # A fixed, scan-independent default is used instead.
    assert 'max-smells: "0"' in ci
    assert "--max-smells 0" in ci
    # Disclosure travels with the copied text itself, not just the page around it.
    assert "browser" in ci.lower()
    assert "may find more" in ci.lower() or "full cli" in ci.lower()


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


def test_hero_frames_the_number_as_coverage_not_quality():
    """A visitor who reads nothing but the hero must still learn that the
    number does not rank prompt quality — and see the figure that says so."""
    html = _html()
    assert "See which governance rules your prompt does not state" in html
    assert "Coverage, not a quality ranking." in html
    # The measured result travels with the claim, not only behind a link.
    assert "+0.061" in html
    assert "p=0.36" in html
    assert "0.863" in html
    assert VALIDATION_URL in html


def test_score_surface_repeats_the_coverage_disclaimer():
    """The disclosure cannot live only in the hero: a visitor who pastes and
    scrolls straight to the ring reads the number with none of the hero in
    view, and that number is what they screenshot."""
    html = _html()
    m = re.search(r"function renderInspect\(result, opts\) \{.*?\n  \}", html, re.S)
    assert m, "renderInspect function not found"
    body = m.group(0)
    assert "This number is coverage, not quality." in body
    assert VALIDATION_URL in body


def test_share_text_does_not_claim_prompt_quality():
    """Share text outlives the page. It is the one artifact that travels to
    readers who never see any disclosure we put on the site."""
    html = _html()
    m = re.search(
        r"function shareText\(overall, tierName, kind\) \{.*?\n  \}", html, re.S
    )
    assert m, "shareText function not found"
    body = m.group(0)
    assert "not a quality ranking" in body
    assert "Structural hygiene only" not in body


def test_validation_study_linked_from_footer():
    """Persistent link for a reader who arrives mid-page or scrolls past."""
    html = _html()
    foot = html[html.find('<footer class="foot">') : html.find("</footer>")]
    assert foot, "footer not found"
    assert VALIDATION_URL in foot


def test_partial_detector_disclosure_survives_the_coverage_reframe():
    """Separate honest disclosure, separate feature: the browser runs 1 of 3
    smell detectors. The governance reframe must not take it out with it."""
    html = _html()
    m = re.search(r"function renderConfigVerdict\(result\) \{.*?\n  \}", html, re.S)
    assert m, "renderConfigVerdict function not found"
    body = m.group(0)
    assert "partial-note" in body
    assert "This browser ran ${ran} of ${total} detectors." in body
    assert (
        "A clean result here is a partial check, not a clean bill of health." in body
    )


def test_readme_headline_is_a_checklist_not_a_score():
    """The headline sells a checklist. "Score" as the noun claims a ranking
    the length-matched study could not demonstrate."""
    md = _readme()
    assert "Free structural score for AI agent prompts" not in md
    assert "### A governance checklist for AI agent prompts" in md


def test_readme_links_validation_study_above_the_fold():
    """The negative result is the credibility play — it belongs in the first
    screen, not in a Limits section a skimmer never reaches."""
    md = _readme()
    assert "docs/validation.md" in md[:2400]


def test_readme_states_the_discrimination_result_with_numbers():
    """Vague hedging is not disclosure. The measured figures ship in prose."""
    md = _readme()
    for stat in ("+0.061", "p=0.36", "0.863", "0.800"):
        assert stat in md, f"validation statistic {stat} missing from README"


def test_readme_draws_the_checklist_versus_benchmark_line():
    """The is/is-not table must name the distinction outright: a checklist
    answers "did you write a rule for X"; a benchmark ranks A against B."""
    md = _readme()
    rows = [
        line
        for line in md.splitlines()
        if line.startswith("|")
        and "checklist" in line.lower()
        and "benchmark" in line.lower()
    ]
    assert rows, "no is/is-not row drawing the checklist vs benchmark line"


def test_readme_charter_carries_discrimination_and_validity_disclosure():
    """The charter is where honesty principles live, so the discrimination
    result and the three low-validity dimensions live there too."""
    md = _readme()
    start = md.find("## Scoring charter")
    end = md.find("## Install", start)
    assert start > 0 and end > start, "scoring charter section not found"
    charter = md[start:end]
    assert "crewscore-hygiene@0.4.0" in charter
    assert "+0.061" in charter
    for dim in ("Cost", "Compliance", "Audit"):
        assert dim in charter, f"charter omits low-validity dimension {dim}"
    assert "docs/validation.md" in charter


def test_readme_documents_040_breaking_changes():
    """0.4.0 drops four fields from config `--json` payloads and changes a
    `fix` exit code. A consumer who upgrades blind breaks; say so."""
    md = _readme()
    start = md.find("## What changed in 0.4.0")
    assert start > 0, "0.4.0 release-notes section not found"
    end = md.find("## CI integration", start)
    assert end > start
    section = md[start:end]
    for field in ("`overall`", "`dimensions`", "`findings`", "`transparency`"):
        assert field in section, f"0.4.0 notes omit dropped field {field}"
    assert "exit" in section.lower()


def test_readme_tier_table_discloses_the_empty_top_half():
    """The tier ladder advertises 90-100 as reachable. Nothing real reaches
    it — the highest score across 1,368 prompts was 50 — so a reader looking
    at the ladder must be told that before they set a threshold against it."""
    md = _readme()
    start = md.find("### Score tiers")
    end = md.find("## Two artifacts", start)
    assert start > 0 and end > start, "score tiers section not found"
    tiers = md[start:end]
    assert "50" in tiers and "1,368" in tiers
    assert "docs/validation.md" in tiers


def test_readme_config_smells_marked_unaffected_by_the_study():
    """The smell detectors replicate published work on a separate corpus.
    The reframe must not read as if they were implicated too."""
    md = _readme()
    start = md.find("## Configuration smells")
    end = md.find("## What changed", start)
    assert start > 0 and end > start, "configuration smells section not found"
    section = md[start:end]
    assert "validation study" in section.lower()
    assert "arxiv.org/abs/2606.15828" in section


def test_readme_never_presents_an_unpublished_version_as_released():
    """Neither 0.3.0 nor 0.3.1 was ever published; PyPI stops at 0.2.7.

    The rule is not "never say 0.3.x" — saying it is *fine and useful* when
    the point being made is that it never shipped, which is what an upgrading
    user needs to know. What must never happen is presenting it as something
    the reader could have, install, or be upgrading from.
    """
    md = _readme()
    if "0.3.1" in md or "0.3.0" in md:
        assert "never published" in md.lower(), (
            "README mentions a 0.3.x version without saying it never shipped"
        )
        assert "0.2.7" in md, "README must name the real last public release"
    # No instruction anywhere can point at an unpublished version.
    for bad in ("pip install crewscore==0.3", "crewscore==0.3.0", "crewscore==0.3.1"):
        assert bad not in md, bad


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
