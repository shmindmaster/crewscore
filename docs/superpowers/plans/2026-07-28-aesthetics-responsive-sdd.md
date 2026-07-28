# Plan: Aesthetics + mobile/desktop parity (0.2.8)

**Repo:** `C:\Repos\shmindmaster\crewscore`  
**Branch:** `feat/aesthetics-responsive-0.2.8`  
**Goal:** Distinctive preflight aesthetic for builder + HN audiences; fully usable on mobile and desktop; Linear backlog current.

## Audiences

| Audience | Aesthetic need | Functional need |
| --- | --- | --- |
| Agent builders / AI eng | Instrument / preflight console — amber caution, mono, checklist | Dense desktop layout; CI handoff; keyboard + large CTAs |
| HN / OSS | Honest, non-hype, recognizable screenshot | Capability stamp always visible; no AI-gradient cliché |
| Mobile (phone paste → score) | Same brand at small size | 44px touch targets; sticky stages; safe-area; no hidden honesty chip |

## Global constraints

- TDD: failing tests first for every contract change.
- Honesty: structural pre-gate only; keep "not a red-team", builder-first hero, vendor secondary.
- Offline web (`score-engine.js`); no LLM SDKs.
- Preserve existing contract strings in `tests/test_web_ux.py` and `tests/test_web_engine.py`.
- Prefer small commits; no force-push main.
- Encoding: use ASCII-safe punctuation in HTML text nodes where UTF-8 corruption appears (`·` and en-dashes OK if file is UTF-8).

## Tasks

### Task 1 — Responsive + a11y contract tests (RED)

**TDD:** Add to `tests/test_web_ux.py`:

1. `test_mobile_touch_targets` — CSS defines min touch height ≥44px for `.btn`, `.btn-sec`, `.chip`, `.stage-pill` (assert `min-height:44px` or `min-height: 2.75rem`).
2. `test_safe_area_padding` — body or wrap uses `env(safe-area-inset-*)`.
3. `test_sticky_stages_mobile` — stages nav has sticky positioning under a mobile media query (or class `stages-sticky` / `position:sticky` near `.stages`).
4. `test_cap_chip_mobile_visible` — cap-chip is **not** `display:none` on mobile; use compact chip or keep visible (`@media` must not hide honesty).
5. `test_desktop_density` — desktop media query (`min-width:900px` or similar) widens wrap and/or uses multi-column gaps layout markers (`data-layout="desktop"` or `max-width:960px` / `.wrap` wider).
6. `test_stage_nav_buttons` — stage pills are focusable controls (`role="button"` or `<button>`) for completed-stage jump.
7. `test_ci_gate_copy_in_export` — static markers: `ci-block` / "Gate this in CI" / `shmindmaster/crewscore@v1` still present in page source or documented in render path (keep `ci-block` class in CSS + help text).

**Done when:** new tests fail for missing pieces; existing 8 still pass.

---

### Task 2 — Implement responsive + stage navigation (GREEN)

**Files:** `index.html` only (CSS + markup + small JS).

1. Touch targets: `.btn`, `.btn-sec`, `.chip`, `.stage-pill`, `.answers button` → `min-height:44px` (and adequate padding).
2. `padding` with `env(safe-area-inset-top/bottom/left/right)` on `body`.
3. Mobile (`max-width:640px`): `.stages { position: sticky; top: 0; z-index: 20; background: ... }` with bottom safe padding.
4. Remove ` .cap-chip{display:none}` — instead shrink font / allow wrap on small screens.
5. Stage pills: use `<button type="button">` with aria-current when on; JS `jumpToStage` only enables stages already reached (prompt always; inspect/act/export when decks not hidden / lastAgent set).
6. Desktop (`min-width:900px`): `.wrap { max-width: 960px }`; optional inspect two-column via CSS for score-hero + dims if simple.
7. Fix corrupted punctuation in deck heads (replace mojibake with `·` or `-`).

**Done when:** Task 1 tests green; full pytest green.

---

### Task 3 — Aesthetic signature polish (GREEN, same suite)

1. Stronger preflight identity: corner tick marks on `.deck` (1px amber L-brackets via box-shadow or pseudo), slightly more terminal CRT grid restraint.
2. Stage pills: numbered mono instrument look (already partially); active state with amber left bar.
3. Score hero: optional thin radar-ring CSS (conic/border) behind big score — distinctive screenshot without clutter.
4. Mobile sticky primary CTA bar only on prompt deck (`#mobile-score-bar`) with `Run score` mirroring main button — hide on desktop.
5. Share canvas colors already match tokens — leave unless broken.

**TDD:** extend tests:
- `test_preflight_aesthetic_tokens` — CSS vars `--amber`, `--mono` present; `.deck` has corner or `box-shadow` instrument treatment; score-hero has `score-ring` or similar marker.
- `test_mobile_score_bar` — `#mobile-score-bar` present with media hide/show.

**Done when:** tests green; no hero/honesty regressions.

---

### Task 4 — Version note + Linear + ship prep

1. Bump to `0.2.8` only if product behavior changed enough to publish; otherwise ship as web-only Pages deploy (HTML is not versioned by PyPI). Prefer **web-only** commit without PyPI bump unless CLI changed — **no PyPI bump required** for pure HTML.
2. Comment SH-2339 + create/close Linear issues for this slice.
3. PR to main when green.

## Parallelism

- Linear create/comment || Task 1 tests (no conflict).
- Tasks 1→2→3 sequential (shared `index.html` / `test_web_ux.py`).
- Task 4 after 3.

## Out of scope

- SH-2366 PMF interviews (human process).
- SH-2344 adversarial mode.
- Soft announce posting (user-owned).
