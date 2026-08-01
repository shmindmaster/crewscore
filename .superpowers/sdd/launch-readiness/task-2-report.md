# Task 2 Report: Deterministic coverage delta asset + launch measurement runbook

## Scope
- Task 2 from `.superpowers/sdd/launch-readiness/task-2-brief.md`
- Repo and environment: `C:\wt\crewscore\launch-measurement-v069`
- Worktree-only edits, no deploy/publish/PR.

## Decisions and outcomes
- Implemented deterministic demo generation from fixture and live scorer in `scripts/generate_demo_asset.py`.
- Kept `docs/demo.svg` deterministic and proofed to:
  - show `8 / 23 -> 9 / 23`,
  - include the closed control `human_gate.approval_required`,
  - include explicit text for non-runtime proof.
- Added strict analytics event schemas in `analytics.js` and `crewscore/metrics.py` with aligned schema version `2026-07-31`.
- Enforced bound checks (enums, numeric ranges, lengths) at capture boundary and in Python append/validate paths.
- Added/kept tests to detect:
  - unknown/missing/extra property rejection,
  - non-schema values blocked before network,
  - malicious string sentinels absent from runtime body,
  - prompt text not sent in analytics.
- Added launch measurement runbook: `docs/launch-measurement.md`.
- Removed scratch artifact: `tmp_test_prompt.md`.

## Files changed
- `analytics.js`
- `assets/site.js`
- `crewscore/metrics.py`
- `docs/demo.svg`
- `tests/test_analytics_claims.py`
- `tests/test_demo_asset.py`
- `tests/test_metrics.py`
- `scripts/generate_demo_asset.py`
- `docs/launch-measurement.md` (new)
- `.superpowers/sdd/launch-readiness/progress.md`
- `.superpowers/sdd/launch-readiness/task-2-report.md` (new)

## Exact commands and results
- `.venv\Scripts\python.exe scripts\generate_demo_asset.py --output docs\demo.svg`
  - Result: deterministic output generated and validated by fixture tests.
- `py scripts\generate_dist_pack.py`
  - Result: regenerated `_production\launch\dist-pack` locally.
- `.venv\Scripts\python.exe -m pytest -q tests\test_demo_asset.py tests\test_metrics.py tests\test_analytics_claims.py tests\test_web_ux.py`
  - Result: `55 passed`
- `npm run test:web -- --project=chromium`
  - Result: `20 passed`
- `npm run test:web`
  - Result: `77 passed`, `3 skipped`
- `.venv\Scripts\python.exe -m pytest`
  - Result: `534 passed`, `1 skipped`
- Fix-review follow-up validation (Task 2 findings):
  - `.venv\Scripts\python.exe -m pytest -q tests/test_metrics.py tests/test_analytics_claims.py`
    - Result: `41 passed`
  - `.venv\Scripts\python.exe -m pytest -q tests/test_demo_asset.py tests/test_metrics.py tests/test_analytics_claims.py tests/test_web_ux.py`
    - Result: `63 passed`
  - `.venv\Scripts\python.exe -m pytest`
    - Result: `542 passed`, `1 skipped`

## Asset paths generated/updated
- `docs/demo.svg`
- `_production\launch\dist-pack\*`

## Self-review findings
- Schema parity is locked with tests; Python and JS allowlists and schema version are aligned.
- Coverage claims in `docs/demo.svg` remain derived from `assets/demo-fixture.js` + scorer output; no manual score edits.
- Launch runbook explicitly separates telemetry from activation/adoption/PMF.
- Privacy boundary still depends on strict enum/range filtering and opt-out-safe call site behavior (already validated by tests).

## Task 2 fix-review evidence (telemetry parity)
- Findings:
  - `_validate_int` now rejects booleans before `int` checks so `True/False` fail parity with `Number.isInteger`.
  - `append_event` now stores validated canonical properties (the sanitized output from `_validate_event`) rather than raw input.
- Added regression tests in `tests/test_metrics.py` to cover all integer-bearing fields:
  - `cs_score`: `overall_bucket`, `controls_found`, `smell_count`, `delta_bucket`
  - `cs_fix_review`: `dims_to_fix_count`
  - `cs_fix_apply`: `controls_found`
- Exact rejection example:
  - `append_event({}, "cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": True, "controls_found": 8})` now raises `ValueError`.

## Continuation closeout (2026-08-01)
- Terminal-review findings validated again in this run:
  - Arbitrary output-dir deletion blocked (via staging-then-copy flow in `scripts/generate_dist_pack.py`).
  - Transactional pack preservation preserved (`scripts/generate_dist_pack.py` uses one temporary staging directory).
  - Corpus fail-closed behavior proven by `tests/test_launch_copy.py::test_generate_dist_pack_fails_closed_on_bad_corpus` (5 focused cases: malformed JSON, missing corpus, zero-evidence, unparseable structure, and empty mutation restoration).
  - X-post limit enforced in `tests/test_launch_copy.py::test_generate_dist_pack_x_channel_respects_post_limit` (<=280 chars).
  - Telemetry event order and bounded share telemetry re-verified via Playwright:
    - `npm run test:web -- --project=chromium` (`20 passed`)
    - `npm run test:web` (`77 passed, 3 skipped`) with the share telemetry test fixed for webkit.
  - coding-config/non-score event separation confirmed by no `cs_score` emission when scoring AGENTS-like payloads (analytics schema tests).
  - JS/Python schema payload parity confirmed by checksum/sanity fixtures and shared schema checks.
  - Backward-compatible one-argument `validate_props` path retained for direct dict payloads.
  - Wrapped demo SVG text and live derive path verified.
  - Docs claims updated to portable phrasing in `docs/launch-measurement.md`.
  - Dynamic `lastCaptureError` probe remains tested in `tests/test_metrics.py`.
- Evidence capture from this run:
  - `.venv\Scripts\python.exe -m pytest -q tests/test_launch_copy.py tests/test_branding_copy.py tests/test_demo_asset.py tests/test_metrics.py tests/test_analytics_claims.py tests/test_web_ux.py` → `87 passed`.
  - `npm run test:web -- --project=chromium` → `20 passed`.
  - `npm run test:web` → `77 passed, 3 skipped`.
  - `.venv\Scripts\python.exe -m pytest` → `558 passed, 1 skipped`.
  - `.venv\Scripts\python.exe -m pytest -q tests/test_launch_copy.py -k "preserves_unrelated_files or fails_closed_on_bad_corpus"` → `5 passed, 7 deselected`.
- Canonical local dist-pack regeneration run:
  - `.venv\Scripts\python.exe scripts/generate_dist_pack.py`.
  - Generated package at `_production\launch\dist-pack` with `version=0.6.9` and checksum `eac4107f...`.
  - Prior-pack preservation checks are now represented by the above launch-copy tests (especially stale-state/diff invariance).
- Current EOF hygiene for `docs/launch-copy.json`: removed trailing blank line in staged payload, preserving JSON integrity.

## Remaining concerns
- Full-browser suite remains environment-dependent on Playwright availability.
- `_production\launch\dist-pack` remains gitignored by convention and is not committed.

## Commit traceability
- Fix review scope: `e22d670..bf91a45`
- Implementation/fix commit: `bf91a45`
- Cleanup/test/report follow-up commit: `de40abc` (removes duplicate validation, extends append-path regression coverage, and corrects evidence).
