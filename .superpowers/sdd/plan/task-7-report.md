# Task 7 legacy analytics schema compatibility

## Outcome

- `schema_payload()` again returns the exact twelve-property allowlist published under `SCHEMA_VERSION = "2026-07-30"`.
- The separately versioned `capture_schema_payload()` continues to expose `traffic_class` under `CAPTURE_SCHEMA_VERSION = "2026-07-31"`.
- Event validation, browser parity, transport behavior, and event names are unchanged.

## TDD evidence

- Added a literal regression pinning the published legacy property set and requiring `traffic_class` in the capture contract before changing production code.
- The initial focused run failed as expected because `traffic_class` was present as an extra legacy property.
- After separating the immutable legacy set from the capture allowlist, the regression and complete metrics test file passed.

## Validation

- `py -m pytest tests/test_metrics.py::test_legacy_schema_payload_keeps_published_properties_while_capture_adds_traffic_class -q` — 1 passed.
- `py -m pytest tests/test_metrics.py -q` — 32 passed.
- `py -m pytest -q` — 581 passed, 1 skipped.
- `git diff --check` — passed (Git reported only the repository's Windows line-ending notices).

## Scope and delivery state

Only `crewscore/metrics.py`, its focused regression test, and this report changed. No scoring, browser code, analytics transport, ruleset, package version, dependencies, hero, or release surface changed. This is implemented and locally validated only; it has not been pushed, merged, or deployed.
