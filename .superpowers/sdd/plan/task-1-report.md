# Task 1 Report - Candidate analytics classification

## Outcome

Implemented the optional `traffic_class` analytics property without changing
event names, scoring/classification behavior, dependencies, ruleset, capture
schema version, or the production-host capture gate.

`traffic_class` is bounded to `production | synthetic_qa` in the Python and
browser strict-capture schemas. Browser payloads always derive the final value:
`production` by default and `synthetic_qa` only when the production URL carries
`crewscore_test_traffic=true`. Non-production host suppression and opt-out
behavior remain unchanged.

## RED evidence

Tests were added before production implementation.

1. `py -m pytest tests/test_metrics.py -q`
   - Exit 1; 4 failed, 27 passed.
   - Expected failures: `traffic_class` was an unexpected strict-capture
     property and absent from the published capture schema.
2. `py -m pytest tests/test_analytics_claims.py::test_browser_capture_labels_human_qa_without_weakening_nonproduction_suppression -q`
   - Exit 1; 1 failed.
   - Expected failure: emitted browser properties had no `traffic_class`.

## GREEN and verification evidence

1. `py -m pytest tests/test_metrics.py tests/test_analytics_claims.py -q`
   - Exit 0; 57 passed.
2. `py -m pytest -q`
   - Exit 0; 573 passed, 1 skipped in 42.81 seconds.
3. `npx playwright test web-tests/checker.spec.mjs --project=firefox --grep "applying one selected|developer mode exposes"`
   - Exit 0; 2 passed.
   - This reran the two unrelated Firefox interaction failures from the first
     all-engine browser run.
4. `$env:CI='1'; npm run test:web`
   - Exit 0; 80 passed, 3 skipped, 1 flaky after configured retry.
   - The flaky retry was an unrelated Firefox review-flow interaction in
     `web-tests/checker.spec.mjs:221`; no analytics assertion failed.
5. `git diff --check`
   - Exit 0.
6. `git merge-base --is-ancestor 86b39ed HEAD`
   - Exit 0; required anchor remains in ancestry.

## Changed files

- `analytics.js`: adds the bounded property, publishes it in every event
  schema, derives the browser value from the explicit QA URL flag, and retains
  the existing `crewscore.ai` gate.
- `crewscore/metrics.py`: adds equivalent bounded property/schema definitions,
  all-event optional-property metadata, and allowlist parity.
- `tests/test_metrics.py`: strict Python validation and all-event schema tests.
- `tests/test_analytics_claims.py`: browser-runtime coverage for production
  default, explicit human QA classification, and non-production suppression.
- `docs/launch-measurement.md`: documents the property, default, QA marker,
  and privacy boundary.

## Self-review

- No event names, dependency files, score semantics, profile classification,
  ruleset identifier, version identifiers, hero copy, or network hostname gate
  were changed.
- The property remains allowlisted, enum-bounded, max-length-bounded, and does
  not admit prompt content.
- Existing sparse 0.6.9 Python validation behavior remains covered by its
  regression tests; strict browser capture remains opt-in/allowlisted.

## Commits

- `6308a28965620dacb426b44fea435be49091a508` - implementation, tests, and
  launch-measurement documentation.
- The report artifact is committed separately as the commit that contains this
  file, because `.superpowers` is intentionally ignored.

## Concern

The all-engine Playwright suite completed successfully under CI retry policy,
but recorded one unrelated Firefox review-flow flake before retry. It does not
exercise the modified analytics boundary. No task-specific test failure
remains.
