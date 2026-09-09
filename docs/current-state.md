# Current State

The CLI scans coding-agent configuration for smells and system prompts for
written-control coverage. The static site runs its generated scoring engine
inside the browser. Coverage does not establish runtime safety; see
[validation.md](validation.md).

The 2026-09-09 portfolio check at `d57a975` passed 639 Python tests in a fresh
isolated Python 3.13 environment. The old local virtual environment pointed
to a removed Python installation. A frozen npm installation also replaced
stale Playwright 1.62.0 modules with the lockfile's 1.62.1.
The existing upstream upgrade to Playwright 1.63.0 was then integrated and
the same full browser suite passed again after frozen installation.

Browser traces then demonstrated that top-level `use.reducedMotion` was
ignored. The corrected `use.contextOptions.reducedMotion` has a browser
canary; animation-specific tests retain their explicit full-motion setting.
The wording-review flow now focuses its heading on open, restores the review
button on cancel, and focuses the rescored heading after Apply. Three new
regressions failed against the preceding implementation; the full candidate
browser suite passes 211 cases with 21 explicit skips across four projects.

Live browser QA also exercised the synthetic 8-of-23 to 9-of-23 local
selection/rescan flow. It sent no prompt or message and made no scoring or
ruleset changes. Website deployment uses the existing GitHub Pages source
(`main`, repository root); PyPI publication is a separate release.
