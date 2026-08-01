# Task 4 report — Candidate CI and review fixes

## Outcome

DONE_WITH_CONCERNS. Task 4's two scoped release-blocking fixes are implemented and committed on `agent/launch-measurement-v069`. No push or merge was performed.

## RED

- `py -m pytest tests/test_demo_asset.py::test_playwright_module_probe_rejects_an_executable_without_playwright -q` failed with `NameError`: the capability probe did not exist.
- `npm run test:web -- --grep "non-compact SVG cards show"` failed in Chromium: the returned LinkedIn SVG contained `<text ...></text>` where the computed `15 may be missing` subtitle belonged.

## GREEN

- The SVG layout test now finds `node`, verifies `require.resolve("playwright")` from the repository, and skips with an explicit module-unavailable reason if that probe fails. The dedicated browser job configuration was not changed.
- Non-compact share cards render the existing computed `${missing.length} may be missing · ${gapLine}` subtitle. Compact badge wording remains `Written-control coverage, not runtime proof`.
- Focused green:
  - `py -m pytest tests/test_demo_asset.py::test_playwright_module_probe_rejects_an_executable_without_playwright tests/test_demo_asset.py::test_demo_svg_gap_panel_layout_stays_within_panels -q` — 2 passed.
  - `npm run test:web -- --grep "non-compact SVG cards show"` — Chromium passed; three intentionally non-Chromium projects skipped.
  - `npm run test:web -- --grep "sanitized result links and SVG cards" --update-snapshots` — Chromium passed; snapshot updated for the intended subtitle.
- Full Python:
  - `py -m pytest -q` — 574 passed, 1 skipped (21.04s).

## Full browser concern

`npm run test:web` was run twice. The Task 4 Chromium SVG regression passed both times, but the full suite was not clean because unrelated cross-browser tests failed inconsistently:

- Run 1: Firefox `successful copy actions emit bounded share-method telemetry` missed `copy_result` (81 passed, 6 skipped, 1 failed). Its isolated Firefox rerun passed.
- Run 2: Firefox `imports a mocked public GitHub file and rejects other hosts` did not render the expected invalid-host status, and WebKit `successful copy actions emit bounded share-method telemetry` missed `copy_result` (80 passed, 6 skipped, 2 failed).

No change was made to these unrelated import/telemetry tests under Task 4 scope.

## Files

- `tests/test_demo_asset.py` — Playwright module capability probe and regression.
- `assets/site.js` — non-compact share-card subtitle output.
- `web-tests/checker.spec.mjs` — generated social-card and compact-badge regression.
- `web-tests/checker.spec.mjs-snapshots/share-card.svg` — expected generated SVG output.

## Commit

- `6278d07 fix(web): restore share-card subtitles`
