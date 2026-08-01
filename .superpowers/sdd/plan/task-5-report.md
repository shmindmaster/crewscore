# Task 5 review-finding closure

## Outcome

- Generated pack files now unlink preserved symlinks before writing, so a generated artifact cannot overwrite a target outside the pack.
- A failure injected after first-time candidate promotion removes the promoted output; existing-pack rollback remains intact.
- Generated share URLs remove `crewscore_test_traffic` while the originating QA session remains classified as `synthetic_qa`.
- The compact `760x180` badge was reproduced as overflowing: the first-gap line ended at y=185 and the coverage caveat began below the viewBox. The compact layout now keeps both text elements within the canvas.

## TDD evidence

- Added symlink, first-promotion rollback, QA-share URL, and browser SVG geometry tests before implementation.
- The initial focused run failed as expected: the external symlink target was overwritten, the failed first promotion left `dist-pack`, and `CrewScoreAnalytics.shareUrl` did not exist.
- The initial compact-badge browser run failed after correcting SVGRect serialization: the first-gap text ended at y=185, outside the 180px viewBox.

## Validation

- `py -m pytest tests/test_launch_copy.py tests/test_analytics_claims.py` — 47 passed.
- `npx playwright test` — 82 passed, 9 expected single-browser skips, 1 unrelated Firefox parallel-run selector flake.
- `npx playwright test web-tests/checker.spec.mjs --project=firefox --grep "applying one selected control"` — passed in isolation.
- `py -m pytest` — 579 passed, 1 skipped.
- `git diff --check` — passed.

## Scope and delivery state

No scoring logic, event/schema names, ruleset, version, dependencies, hero, or release copy changed. This is implemented and locally validated only; it has not been pushed, merged, or deployed.
