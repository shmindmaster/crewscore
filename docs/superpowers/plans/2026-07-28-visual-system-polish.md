# Plan: Visual system polish — color hierarchy + type roles

**Repo:** `C:\Repos\shmindmaster\crewscore`  
**Branch:** `feat/visual-system-polish`  
**Why:** Landing is coherent but mid — amber overused, mono overused, score ring soft, panels low contrast. Target: memorable preflight instrument for builders/HN.

## Global constraints

- TDD: fail tests first for new contracts; keep existing `tests/test_web_ux.py` green.
- Honesty strings unchanged: Structural pre-gate, not a red-team, builder-first hero, vendor secondary.
- Offline; no LLM; no cyan AI-default accent.
- Files: primarily `index.html` CSS (+ small JS only if score-ring markup needs class tweak), `tests/test_web_ux.py`.
- Small commits; PR to main when green.

## Design rules (must implement)

### Color hierarchy
1. **Amber is scarce:** primary CTA (`.btn`), active stage left bar / border, capability stamp border only. NOT default link color for all mono labels; body links may use a softer accent `--link` or muted amber at lower opacity.
2. **Panel lift:** `--panel` at least one clear step lighter than `--bg`, or add stronger `border-color` / inset so cards read as surfaces.
3. **Kill or thin page grid:** remove `repeating-linear-gradient` body grid OR drop opacity to ≤0.12 so it is atmospheric only.
4. **Score ring:** thin annular track (border-based or conic with transparent center), not soft filled gold glow disc. Keep class `score-ring`.
5. **Weak banner:** keep functional red tint; optional max-width / calmer padding — no behavior change.

### Type roles
6. **Sans for UI chrome:** `.stage-pill`, `.deck-head h3`, `.btn` labels use `var(--sans)` (or mixed: number mono, label sans). **Mono reserved for:** `.score-big`, rule codes, `.ci-block`, textarea, brand mark "CS", footer codes, dim scores.
7. **Type scale tokens** in `:root`:
   - `--fs-xs: 0.72rem` · `--fs-sm: 0.8rem` · `--fs-md: 0.95rem` · `--fs-lg: 1.05rem` · `--fs-hero: clamp(1.55rem,4vw,2.15rem)` · `--fs-score: clamp(2.75rem,8vw,3.6rem)`
8. Soften all-caps on stages if still uppercase: keep short labels but font-weight 600 sans, letter-spacing modest (≤0.06em).

### Preserve
- Touch targets 44px, safe-area, sticky stages, mobile-score-bar, deck-instrument corners, cap-chip visible on mobile, desktop 960px.

## Tasks

### Task 1 — RED design-system contracts
Add tests in `tests/test_web_ux.py`:
- `test_type_scale_tokens` — `:root` has `--fs-xs` through `--fs-hero` or `--fs-score`
- `test_mono_reserved_not_all_chrome` — `.stage-pill` CSS block uses `var(--sans)` or `IBM Plex Sans` (not only mono as sole font-family)
- `test_score_ring_annular` — `.score-ring` rules include transparent center technique (`transparent` in gradient or solid bg with border ring) and do not rely only on soft multi-stop gold fill without ring structure
- `test_body_grid_restrained` — either no `repeating-linear-gradient` on body, OR comment/marker `/* grid atmospheric */` with opacity channel ≤ `.15` in that gradient stop
- `test_panel_lifted_from_bg` — `--panel` value ≠ `--bg` and not identical hex

Done when: new tests fail on current main CSS; old tests still pass.

### Task 2 — GREEN implement visual system
Apply design rules 1–8 in `index.html` only. Re-run full `py -3.13 -m pytest`. Commit.

### Task 3 — Visual smoke (controller or implementer)
Playwright local serve: desktop + mobile landing/scored screenshots under `_product-experience/ui-polish-*.png`. Confirm amber scarcity and sans stages in screenshot.

## Parallelism
Task 1 then 2 sequential (same files). Linear comment parallel OK.
