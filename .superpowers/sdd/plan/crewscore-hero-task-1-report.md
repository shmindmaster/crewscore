# CrewScore hero Task 1 report

Status: DONE

## Commit

- Product implementation: `b79b0b6556547a8ed845efbe805ef47653b9407a`

## Outcome

Added a responsive native product stage beside the existing CrewScore hero copy and CTAs. The finite demonstration calls the existing browser-local `CrewScoreEngine` against the existing synthetic fixture, derives the 8/23 result and first named gap from that result, reads the selected human-approval wording from the generated engine contract, and recomputes the 9/23 result. Autoplay does not use the full checker, visitor prompt text, analytics, storage, URLs, cards, or network services.

## Changed paths

The product commit changes exactly five paths:

1. `index.html`
2. `assets/site.css`
3. `assets/site.js`
4. `tests/test_web_ux.py`
5. `web-tests/checker.spec.mjs`

## Automated verification

- `py -m pytest -q`
  - 582 passed, 1 skipped.
- `npm run test:web -- --reporter=line`
  - Initial product implementation: 105 passed, 15 expected skips.
  - After adding the independent-review regression: 109 passed, 15 expected skips.
  - After the accessibility review fixes: 116 passed, 15 expected skips, 1 unrelated WebKit details-toggle retry.
  - Projects: Chromium, Firefox, WebKit, and mobile Chromium.
- `npx playwright test web-tests/checker.spec.mjs --grep "initial autoplay emits" --reporter=line`
  - 4 passed, one in each browser project.
- `$env:CI='1'; npx playwright test web-tests/checker.spec.mjs --project=chromium --project=mobile-chromium --grep "initial autoplay emits|native product remains" --retries=0 --reporter=line`
  - Exact PR-CI remediation gate: 3 passed, 1 expected project skip.
  - The autoplay test sets the approved 390x844 launch viewport before navigation; the geometry test requires at least 200 visible pixels, retaining a 20-pixel buffer above the 180-pixel launch requirement.
- `npx playwright test web-tests/checker.spec.mjs --grep "explicit replay gates|runtime reduced-motion|initial autoplay emits|keyboard operable" --retries=0 --reporter=line`
  - Accessibility review gate: 16 passed across all four browser projects.
- `npx playwright test web-tests/checker.spec.mjs --grep "explicit play activation|explicit replay gates" --retries=0 --reporter=line`
  - Separate Play/Replay listener coverage: 8 passed across all four browser projects.
- `npx playwright test web-tests/checker.spec.mjs --grep "native hero animation" --retries=0 --reporter=line`
  - Proportionate post-review hero gate: 33 passed, 3 expected project skips.
- `npx playwright test web-tests/checker.spec.mjs --project=webkit --grep "developer mode exposes technical detail" --retries=0 --reporter=line`
  - Isolated rerun of the unrelated full-suite retry: 1 passed.
- `git diff --check`
  - Clean.
- `git ls-files --eol index.html assets/site.css assets/site.js tests/test_web_ux.py web-tests/checker.spec.mjs`
  - All five changed paths reported `i/lf w/lf`.

The browser regressions cover engine-derived 8-to-9 parity, first named gap, finite completion, reduced motion, Play/Pause/Replay keyboard operation, offscreen and document-hidden pause/resume, analytics silence from before page/script initialization through initial autoplay, existing explicit demo-event compatibility, privacy leakage boundaries, offline replay, accessibility, and first-viewport geometry without horizontal overflow.

Accessibility review remediation removes the clipped read-only prompt from the tab order, keeps the stable summary semantic, gates a polite `role=status` announcement region behind explicit Play/Replay activation, verifies autoplay leaves that region inert, and retains the motion `MediaQueryList` so a runtime switch to reduced motion cancels timers and immediately renders the complete static before/after state.

## Interactive browser evidence

The pinned Playwright CLI was run against the repository static server.

- Wide, 1440x900: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-wide.png`
- Tablet, 768x1024: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-tablet.png`
- Mobile CI fix, 390x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-mobile-ci-fix.png`

The product stage was visible in the first viewport at all three sizes. The final mobile capture shows the tighter one-row navigation and a substantial product slice while preserving the headline, copy, both CTAs, trust chips, readability, and no horizontal overflow. Replay and Pause were exercised interactively at the engine-derived 8/23 first-gap state. Browser console inspection returned zero errors and zero warnings. Request inspection during autoplay returned no non-static requests; only the page's static assets were observed.

## Scope boundaries

- No scoring formulas, rules, ruleset identifier, package version, dependencies, generated engine, fixture, analytics schema, privacy behavior, release artifact, or full-checker behavior changed.
- No new analytics event or property was introduced.
- Hero scores, gap, and selected wording are runtime-derived; the page and hero script do not contain a second literal 8/23 or 9/23 display contract.
- Reduced motion disables autoplay and renders a complete static before/after state.
- The sequence runs once, stops, pauses when offscreen or document-hidden, and resumes from the same state.
