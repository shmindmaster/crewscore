# CrewScore hero Task 1 report

Status: DONE

## Commit

- Product implementation: `b79b0b6556547a8ed845efbe805ef47653b9407a`
- Current-review remediation: `ca19f79c334ad56f8ea41d4eef45529762f2c8c4`
- Linux narrow-layout remediation: `3d821ac6361bdce31638d90b8071fcdf2709e11a`
- Mobile boundary and Pause announcement remediation: `54c2b14a51b717eabead9f24e49147ff4406a42f`
- Hosted 390-pixel product-visibility remediation: `dc48bcc85cab9cdf7b8bd53ee3b676ce50eb40f0`
- Hosted 320-pixel visibility-buffer remediation: `f73500e29a40d391e3817962cddf4448bc003050`

## Outcome

Added a responsive native product stage beside the existing CrewScore hero copy and CTAs. The finite demonstration calls the existing browser-local `CrewScoreEngine` against the existing synthetic fixture, derives the 8/23 result and first named gap from that result, reads the selected human-approval wording from the generated engine contract, and recomputes the 9/23 result. Autoplay does not use the full checker, visitor prompt text, analytics, storage, URLs, cards, or network services.

The current-review remediation confines the two-column hero and compact mobile navigation to the homepage, restores ordinary vertical flow and complete navigation on long-form pages, prevents horizontal clipping at 320 pixels, and treats the generated canonical fixture as required. If that asset is missing, the hero displays a stable unavailable state and disables its demo controls without emitting analytics or network traffic; the full checker remains functional.

Exact-head PR run `30705689764`, job `91384271094`, exposed a 320-pixel Linux font-metric edge: the document client width was 320 while a homepage descendant expanded the scroll width to 332. The trace proves that the served CSS SHA-1 was `616182696bb8807acd27d0fdc81e328d5f8abe1e`, exactly matching the reviewed source, but the old test retained only aggregate page width and therefore cannot identify the historical leaf element retroactively. The remediation removes the two intrinsic-width pressure points instead of clipping overflow: single-column grids now use a zero minimum track and zero-minimum children, while the homepage header intentionally stacks below 340 pixels. The strict assertion remains and now records every out-of-viewport offender with its selector and bounds if the condition recurs.

The final exact-review remediation keeps the compact “Written-control coverage, not runtime proof” boundary visible beside the mobile hero CTAs at 320 and 390 pixels. An explicit Pause activation now announces “Demo paused” through the gated polite status region; autoplay, programmatic Pause, offscreen Pause, and document-hidden Pause remain silent. The generic scored-with-no-gap branch now truthfully reports that no written-control gap was detected instead of reverting to a waiting message; the fixed 8-to-9 fixture continues to have a named gap in both result states.

Hosted exact-head run `30707014234`, job `91387763640`, then exposed a deterministic 390x844 Chromium visibility failure: the native product slice was 147.0625 pixels against the unchanged strict 200-pixel requirement, although horizontal overflow remained absent. The hosted screenshot showed that Linux font metrics rendered the 11vw/3rem mobile headline across four large lines and pushed the product stage down to approximately 697 pixels. The remediation changes only the homepage mobile headline scale to `clamp(2.05rem, 9vw, 2.5rem)`. The coverage-not-runtime-proof boundary, both CTAs, trust chips, and the strict product-visibility threshold remain intact. At 390x844 the product now begins at 607.296875 pixels, leaving 236.703125 visible pixels and a 36.703125-pixel margin above the required threshold.

The next exact-head run `30707457455`, job `91388925271`, proved the 390-pixel fix held but exposed a deterministic 320x844 Chromium edge: all three attempts showed 117.515625 visible pixels against the unchanged 120-pixel requirement. The 320-pixel hosted screenshot showed all required content intact but only a thin product slice below it. A homepage-only `max-width: 340px` adjustment reduces header/hero vertical padding and gaps, slightly reduces the narrow headline from 1.95rem to 1.85rem, and tightens only the headline, trust-chip, and safety-boundary spacing. It does not remove or hide the boundary, CTAs, trust chips, identity, or mode control. In the pinned Linux image the resulting product slice is 273.8125 pixels at 320 and 297.984375 pixels at 390, with zero overflow; the Windows comparison is 243.640625 and 236.703125 pixels respectively. This leaves a deliberate margin rather than another threshold edge.

## Changed paths

The product commit changes exactly five paths:

1. `index.html`
2. `assets/site.css`
3. `assets/site.js`
4. `tests/test_web_ux.py`
5. `web-tests/checker.spec.mjs`

## Automated verification

- `py -m pytest -q`
  - Hosted 320-pixel buffer head: 584 passed, 1 skipped.
- `npm run test:web -- --reporter=line`
  - Initial product implementation: 105 passed, 15 expected skips.
  - After adding the independent-review regression: 109 passed, 15 expected skips.
  - After the accessibility review fixes: 116 passed, 15 expected skips, 1 unrelated WebKit details-toggle retry.
  - Current head: 122 passed, 21 expected project skips, 1 unrelated Firefox interaction retry; the isolated retry passed 1/1.
  - Linux narrow-layout head, local: 121 passed, 21 expected project skips, 2 unrelated copy-telemetry retries; both passed on retry.
  - Linux narrow-layout head, Playwright 1.62.0 Linux container: 123 passed, 21 expected project skips, zero retries or failures.
  - Mobile-boundary/Pause head, local: 127 passed, 21 expected project skips, zero retries or failures.
  - Hosted-visibility remediation head, local: 127 passed, 21 expected project skips, zero retries or failures.
  - Hosted 320-pixel buffer head, local: 127 passed, 21 expected project skips, zero retries or failures.
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
- `npx playwright test web-tests/checker.spec.mjs --project=chromium --grep "native product remains|mobile subpages retain|missing canonical demo fixture" --reporter=line`
  - Current-review remediation gate: 3 passed. Covers 320/390 homepage overflow and visibility, 320/390 privacy-page navigation and vertical flow, and a missing generated fixture with an unaffected full checker.
- `npx playwright test web-tests/checker.spec.mjs --project=chromium --grep "native product remains|mobile subpages retain" --retries=0 --reporter=line`
  - Linux narrow-layout focused gate: 2 passed on Windows and 2 passed in the pinned Linux container. At 320 pixels it additionally requires a stacked header whose CrewScore brand and Developer-mode control are contained by the site header.
- `docker run --rm --ipc=host ... mcr.microsoft.com/playwright:v1.62.0-noble ... CI=1 npm run test:web -- --reporter=line`
  - Pinned image digest: `sha256:baed2032d533817f3dbe6425de795788430ba345e819a1201337009ba17c9d07`.
  - Full Linux four-project result: 123 passed, 21 expected project skips, zero retries or failures.
- `npx playwright test web-tests/checker.spec.mjs --grep "explicitly activated pause|initial autoplay emits|pauses offscreen|native product remains" --retries=0 --reporter=line`
  - Mobile-boundary/Pause focused gate: 10 passed, 6 expected project skips across all four projects.
  - Matching pinned Linux Chromium subset: 4 passed with retries disabled.
- `npx playwright test web-tests/checker.spec.mjs --project=chromium --grep "native product remains" --retries=0 --repeat-each=3 --reporter=line`
  - Hosted-visibility remediation gate: 3 consecutive passes on Windows and 3 consecutive passes in `mcr.microsoft.com/playwright:v1.62.0-noble`, with retries disabled.
  - The existing strict assertions remain unchanged: at least 200 visible pixels at 390x844, at least 120 visible pixels at 320x844, no horizontal overflow, a visible safety boundary at both widths, exact boundary copy, and contained 320-pixel header controls.
  - Hosted 320-pixel buffer remediation: another 3 consecutive Windows passes and 3 consecutive pinned-Linux passes, with retries disabled and no threshold changes.
- Temporary rendered-geometry probe against the same pinned Linux image, removed after verification
  - Three consecutive runs each measured 273.8125 visible pixels at 320x844 and 297.984375 pixels at 390x844, with zero overflow.
- `npx playwright test web-tests/checker.spec.mjs:64 --project=firefox --reporter=line`
  - Isolated rerun of the unrelated full-suite interaction retry: 1 passed.
- `npx playwright test web-tests/checker.spec.mjs --project=webkit --grep "developer mode exposes technical detail" --retries=0 --reporter=line`
  - Isolated rerun of the unrelated full-suite retry: 1 passed.
- `git diff --check`
  - Clean.
- `git ls-files --eol index.html assets/site.css assets/site.js tests/test_web_ux.py web-tests/checker.spec.mjs`
  - All five changed paths reported `i/lf w/lf`.

The browser regressions cover engine-derived 8-to-9 parity, first named gap, finite completion, reduced motion, Play/Pause/Replay keyboard operation, activation-gated Pause announcements, silent programmatic/passive pauses, offscreen and document-hidden pause/resume, analytics silence from before page/script initialization through initial autoplay, existing explicit demo-event compatibility, privacy leakage boundaries, offline replay, accessibility, homepage-only layout, mobile boundary visibility, subpage reading order/navigation, missing-fixture containment, and first-viewport geometry without horizontal overflow.

Accessibility review remediation removes the clipped read-only prompt from the tab order, keeps the stable summary semantic, gates a polite `role=status` announcement region behind explicit Play/Replay/Pause activation, verifies autoplay and passive pauses leave that region inert or unchanged, and retains the motion `MediaQueryList` so a runtime switch to reduced motion cancels timers and immediately renders the complete static before/after state.

## Interactive browser evidence

The pinned Playwright CLI was run against the repository static server.

- Wide, 1440x900: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-wide.png`
- Tablet, 768x1024: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-tablet.png`
- Mobile CI fix, 390x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-hero-mobile-ci-fix.png`
- Narrow homepage review, 320x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-320-review.png`
- Narrow privacy-page review, 320x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-privacy-320-review.png`
- Narrow Linux-overflow remediation review, 320x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-320-linux-overflow-fix.png`
- Mobile boundary visible, 320x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-320-boundary-visible.png`
- Mobile boundary visible, 390x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-390-boundary-visible.png`
- Hosted product-visibility remediation, 390x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-390-product-visibility-fix.png`
- Hosted narrow-buffer remediation, 320x844: `C:\Users\SaroshHussain\.codex\visualizations\2026\08\01\019fbd09-3372-79a0-ae94-51d3a75ab3bd\crewscore-home-320-hosted-buffer-fix.png`

The product stage was visible in the first viewport at all four homepage sizes. The 320-pixel capture preserves CrewScore identity, Developer mode, the headline, both CTAs, trust chips, and a substantial product slice without horizontal overflow. The 320-pixel privacy capture preserves both navigation links and a normal vertical reading order. Replay and Pause were exercised interactively at the engine-derived 8/23 first-gap state. Browser console inspection returned zero errors and zero warnings. Request inspection during autoplay returned no non-static requests; only the page's static assets were observed.

The post-CI 320-pixel capture confirms the intentional stacked header preserves CrewScore identity and the Developer-mode control while both hero CTAs and a larger product slice remain above the fold.

The final 320- and 390-pixel captures confirm the coverage-not-runtime-proof limitation remains legible directly below the trust chips without horizontal overflow or loss of product visibility.

The hosted product-visibility remediation capture confirms the narrower 390-pixel headline now occupies three lines while preserving the safety boundary, both CTAs, trust chips, and 236.703125 pixels of the native product stage in the first viewport.

The 320-pixel buffer capture confirms the compact narrow layout still shows CrewScore identity, Developer mode, the complete headline and supporting copy, both CTAs, all four trust chips, the complete coverage-not-runtime-proof boundary, and 243.640625 pixels of the native product stage above the sticky action.

## Scope boundaries

- No scoring formulas, rules, ruleset identifier, package version, dependencies, generated engine, fixture, analytics schema, privacy behavior, release artifact, or full-checker behavior changed.
- No new analytics event or property was introduced.
- Homepage selectors do not alter privacy, security, rules, documentation, guide, or vendor-page hero flow or mobile navigation.
- The generated fixture is the sole demo source; no built-in fallback prompt remains. Missing-fixture mode is visible, inert, and leaves the manual checker available.
- Hero scores, gap, and selected wording are runtime-derived; the page and hero script do not contain a second literal 8/23 or 9/23 display contract.
- Reduced motion disables autoplay and renders a complete static before/after state.
- The sequence runs once, stops, pauses when offscreen or document-hidden, and resumes from the same state.
