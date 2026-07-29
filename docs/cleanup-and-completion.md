# Cleanup and completion inventory

Branch: `refactor/lean-product-architecture`  
Status: product features **completed**, not gutted. Ruleset unchanged:
`crewscore-hygiene@0.5.0`.

This note records what the lean-product pass **retained**, **completed**,
**consolidated**, and **deferred**, so reviewers do not have to reverse-engineer
intent from the diff alone.

## Product decision

| Approach | Outcome |
| --- | --- |
| First impulse (delete secondary surfaces) | Rejected after owner feedback |
| Chosen approach | Complete thin but useful features; regenerate docs; add drift tests |

## Retained (active product)

| Component | Why |
| --- | --- |
| Core matching / scoring / smells / profiles | Primary product |
| CLI: `test`, `scan`, `fix`, `rules`, `baseline`, `init` | Primary workflows |
| Policy, SARIF, summary, report/badge | CI and report contracts |
| GitHub Action (`action.yml`) | Primary distribution path |
| Browser checker + generated `score-engine.js` | Live product surface |
| `export-eval` | Live-eval handoff (completed) |
| `assess-vendor` + browser vendor checklist | Secondary diligence (completed) |
| `agent-guard` entry point | Cheap compatibility alias |
| Validation corpus harness + published numbers | Honesty contract |
| Demo/media assets (`docs/hero-*`, `demo/`, `scripts/demo/`) | Product demo path; policy documented |
| Runtime deps: `click`, `rich` only | Offline, dependency-light |

## Completed (were thin; now usable)

| Feature | Completion |
| --- | --- |
| `export-eval` | Gap-biased Promptfoo cases, garak probes, ruleset headers, `--provider`, prompt-free manifest |
| `assess-vendor` | Stable JSON schema, control-theme mapping, `next_crewscore_checks`, HTML/console follow-ups |
| Metrics | Python allowlist SoT + parity with `analytics.js` |
| Docs | Architecture, scoring-and-controls, github-action, development regenerated from code |
| `python -m crewscore` | `__main__.py` entry |

## Consolidated (not deleted)

| Old path | New canonical path |
| --- | --- |
| `docs/scoring.md` | Redirect → `scoring-and-controls.md` |
| `docs/scoring-governance.md` | Redirect → scoring-and-controls governance section |
| `docs/ci.md` | Redirect → `github-action.md` |
| Scattered scoring/architecture claims | Regenerated into fewer authoritative pages |

## Deleted / not done

| Item | Status |
| --- | --- |
| Feature removals (vendor, export-eval, metrics, demos) | **Not done** — owner directed complete, not remove |
| Dependency reduction | **N/A** — already only click+rich at runtime |
| Live Promptfoo/garak execution inside CrewScore | Intentionally not implemented |
| Framework runtime adapters | Intentionally deferred (roadmap) |

## Before / after structure (docs)

**Before:** overlapping `scoring.md`, `scoring-governance.md`, thin `architecture.md`,
`ci.md` as sole Action guide, no `development.md`.

**After:**

```
docs/
  architecture.md           # modules + lean target
  scoring-and-controls.md   # formula + charter + governance
  github-action.md          # Action + CI
  development.md            # setup, packaging, media policy
  validation.md             # methodology (unchanged role)
  cli.md                    # CLI reference (updated)
  policies.md               # baselines / SARIF
  next-steps-eval.md        # completed handoff docs
  scoring.md                # redirect
  scoring-governance.md     # redirect
  ci.md                     # redirect
```

Package layout under `crewscore/` is unchanged in modules; secondary modules
gained capability rather than being removed.

## Dependency summary

| Layer | Before | After |
| --- | --- | --- |
| Runtime | click, rich | click, rich (unchanged) |
| Dev | pytest, pyyaml | pytest, pyyaml (unchanged) |
| Optional browser tests | playwright (npm) | unchanged |

No new runtime dependencies. No LLM SDKs.

## Validation evidence

- Local: `pytest` **460 passed** (after docs tests)
- CI on PR: pytest 3.11 / 3.12 / 3.13, browser tests, CrewScore self-test —
  **success**
- Package build: `python -m build` → `crewscore-0.6.0` sdist + wheel

## Remaining risks / deferred work

1. Cost / Compliance / Audit construct validity remains weak (documented).
2. `export-eval` still does not *run* live evals — better handoff only.
3. Large hero media remain in-repo (~3.4 MB); policy prefers lighter embeds
   for new work.
4. `cli.py` remains a large orchestrator; optional split deferred.
5. Version still **0.6.0** until a release cut; CHANGELOG has **Unreleased** notes.
6. Browser cannot detect init-fossilization / lint-leakage smells (disclosed).

## Next release suggestion

Ship as **0.6.1** (additive completions + docs) unless a scoring break appears.
Bump ruleset only if control arithmetic changes.
