# Coverage matrix

One row per capability. The code was read at `e9a1c9b`, and the suites ran at main `16b9e36` (0.6.14; #79 changed only CI triggers and their test). Rungs: Planned, Implemented,
Integrated, Tested, Demonstrated, Production-Verified.

How to read the rung column:

- **Implemented** means the code exists at the path shown (read, not run).
- **Integrated** means the path from entry point to visible result was traced
  in the code ([TECHNICAL.md](TECHNICAL.md#critical-feature-trace) for the
  main one). It was traced by reading, not by a live execution in this pass.
- **Tested** comes from [TESTS.md](TESTS.md). The full suites passed on main's exact SHA `16b9e36` (2026-10-15):
  - pytest: 676 passed on Python 3.11, 3.12 and 3.13;
  - browser E2E: 211 passed;
  - the Action self-test passed.
  So every row below whose test files are listed is Tested at `16b9e36`. The "Test run" column points there.
- **Demonstrated** is claimed only where the delivered film shows it. The film
  `D:\OneDrive - Maya Modest LLC\Videos\Portfolio\CrewScore\01 - One Sentence.mp4`
  was recorded on `e9a1c9b`. It shows `test`, `fix --plan`, `test --require`
  failing then passing, and the `structural_analysis.py` human-gate code. See
  [DEMOS.md](DEMOS.md).
- **Production-Verified** needs a deployed SHA plus a health check and a smoke
  test of the path. The `test` and `--require` rows have that: PyPI 0.6.14, smoke-tested from a clean install on 2026-10-15 (see [TESTS.md](TESTS.md#production-smoke-checks-2026-10-15-after-publish)).

## Deploy facts observed

| Item | Observed |
|---|---|
| PyPI `crewscore` | 0.6.14 published 2026-10-15 by [Release 38735565259](https://github.com/shmindmaster/crewscore/actions/runs/38735565259) from tag `v0.6.14` (`34214b1`); Homepage `https://crewscore.ai/`. Smoke from PyPI passed (see TESTS.md). |
| crewscore.ai | HTTP 200 for `/` and `/score-engine.js` (engine `crewscore-hygiene@0.6.0`); `pages-build-deployment` succeeded on `16b9e36`. |
| Action tag `v2` | The 0.6.14 release job "Move the floating major tag" succeeded (run 38735565259), so `v2` now follows `v0.6.14`. |
| Pages source | `main`, repository root, `CNAME` `crewscore.ai` (from [current-state](../current-state.md); no Pages workflow in the repo) |

## Evidence matrix

Surface: CLI, Action (A), or site (S). Test column lists files that exist in
`tests/` (or `web-tests/`) for the capability, not results.

| Capability | Journey | Surface | Logic module | Integration | Test files | Test run | Demo | Deploy status | Rung evidenced |
|---|---|---|---|---|---|---|---|---|---|
| `test` (score a prompt) | [FUNCTIONAL #1-2](FUNCTIONAL.md) | CLI | `crewscore/cli.py:338`, `scorers/structural_analysis.py:715`, `scoring.py:133` | Traced end to end in [TECHNICAL](TECHNICAL.md#critical-feature-trace) | `tests/test_cli.py`, `test_concept_scoring.py`, `test_structural_analysis.py`, `test_viral_wedge_cli.py`, `test_hero.py`, `test_hero_sequence.py` | see TESTS.md | see DEMOS.md (shown in film) | PyPI 0.6.14; smoke-tested from PyPI | Production-Verified |
| `--require` policy gate | #3, #5 | CLI, A | `crewscore/policy.py:168,262` | Same trace, hops 3, 5, 11, 14 | `tests/test_policy_and_sarif.py`, `test_hero_sequence.py`, `test_demo_workspace.py` | see TESTS.md | see DEMOS.md (exit 2 then 0 in film) | PyPI 0.6.14; smoke exit 2 → 0 from PyPI | Production-Verified |
| `fix` (plan, apply, output) | #7-8 | CLI | `cli.py:1009`, `scorers/fix_patterns.py` | Read; `--plan` path not traced line by line | `tests/test_cli.py`, `test_demo_workspace.py` | see TESTS.md | see DEMOS.md (`fix --plan` in film; `--apply` not shown) | As above | Tested; Demonstrated (`--plan` only) |
| `scan` (repo discovery, contained) | #4-6 | CLI, A | `crewscore/scan.py:151`, `pathsafe.py`, `cli.py:1556` | Read, not traced | `tests/test_scan.py`, `test_scan_containment.py`, `test_redos.py`, `test_extract_inline.py` | see TESTS.md | Not shown in the film | As above | Tested |
| `rules` (open catalog) | #9 | CLI | `crewscore/rules_catalog.py`, `cli.py:795` | Read | `tests/test_rules_catalog.py`, `test_scan.py` | see TESTS.md | Not shown | As above | Tested |
| `export-eval` (Promptfoo and garak starters) | #13 | CLI | `crewscore/export_eval.py:355` | Writes files only; no tool is run | `tests/test_export_eval.py` | see TESTS.md | Not shown | As above | Tested |
| Baseline and regression | #11-12 | CLI, A | `policy.py:309` (`baseline_payload`), `cli.py:1342` | Read | `tests/test_policy_and_sarif.py` | see TESTS.md | Not shown | As above | Tested |
| SARIF 2.1.0 (prompt-free) | #4, #15 | CLI, A | `crewscore/sarif.py:45` | Read; upload to code scanning is a user step, not run here | `tests/test_policy_and_sarif.py`, `test_prompt_free_outputs.py` | see TESTS.md | Not shown | As above | Tested |
| `init` scaffold | #10 | CLI | `cli.py:1380` | Read | `tests/test_hero_sequence.py`, `test_policy_and_sarif.py` (incidental) | see TESTS.md | Not shown | As above | Tested |
| HTML report and SVG badge | #1 | CLI | `crewscore/report.py` | Read | `tests/test_report.py` | see TESTS.md | Not shown | As above | Tested |
| PR/job markdown summary | #4, #15 | CLI, A | `crewscore/summary.py` | Read | `tests/test_summary.py`, `test_prompt_free_outputs.py` | see TESTS.md | Not shown | As above | Tested |
| Prompt-free output gate | all | CLI, A | `crewscore/findings_export.py:27` | Read | `tests/test_prompt_free_outputs.py` (also run at dependency floors in `pytest.yml`) | see TESTS.md | Not shown | As above | Tested |
| Coding-agent config path (smells, no score) | #6 | CLI | `profiles.py:74`, `smells.py`, `scoring.py:68` | Read | `tests/test_profiles.py`, `test_smells.py` | see TESTS.md | Not shown | As above | Tested |
| GitHub Action | #15 | A | `action.yml` | Self-test workflow `crewscore-selftest.yml` exercises the local action in CI (passed at `16b9e36`) | `tests/test_action_manifest.py`, `test_workflow_*.py`; workflow `crewscore-selftest.yml` | see TESTS.md | Not shown | `v2` follows `v0.6.14`; a consumer-side run was not exercised | Tested (self-test run 38736333626) |
| Static browser checker | #16 | S | `crewscore/web_export.py:446,514` -> `score-engine.js` -> `index.html` | Generation boundary traced; page behavior not run here | `tests/test_web_engine.py`, `test_web_ux.py`; `web-tests/checker.spec.mjs` (58 `test(` calls by static count) | see TESTS.md | Not shown in the film | Pages deployed at `16b9e36`, HTTP 200; no production browser smoke | Tested |
| `score-engine.js` parity | all site use | S | `scripts/export_web_engine.py` | Release gate regenerates and diffs it (`release.yml`) | `tests/test_web_engine.py` | see TESTS.md | Not shown | Same as site | Tested |
| Demo workspace builder | #17 | CLI | `scripts/build_demo_workspace.py` | Read | `tests/test_demo_workspace.py` | see TESTS.md | see DEMOS.md (the film's fixture path) | Repo only, not packaged | Tested |
| Validation corpus and stats | #18 | CLI script | `scripts/validate_corpus.py` | Needs network to fetch pinned SHAs; not run | `tests/test_corpus.py`, `test_corpus_harness.py`, `test_corpus_scores.py`, `test_published_numbers.py` | see TESTS.md | Not shown | Published docs: `docs/validation-corpus.md` | Tested |
| Vendor checklist | #14 | CLI | `crewscore/vendor_scorecard.py` | Read | `tests/test_vendor.py` | see TESTS.md | Not shown | As above | Tested |
| Metrics schema and site analytics | site | S | `crewscore/metrics.py`, `analytics.js` | Not traced; endpoint is PostHog (`analytics.js:5`) | `tests/test_metrics.py`, `test_analytics_claims.py` | see TESTS.md | Not shown | Enablement in production not checked | Tested |
| PyPI release pipeline | n/a | CI | `.github/workflows/release.yml`, `cut-release-tag.yml`, `scripts/cut_release.py` | Trusted publishing (OIDC) read in workflow | `tests/test_release_automation.py`, `test_workflow_provenance.py`, `test_packaging_contract.py` | see TESTS.md | n/a | 0.6.14 published through this workflow (cut 38735525380, release 38735565259) | Production-Verified |

Production-Verified rows: `test`, `--require` and the release pipeline (PyPI 0.6.14 plus a clean-install smoke).
The site is deployed at `16b9e36` with HTTP 200 checks, but no browser smoke ran against production; it stays at Tested.

## Integrations

| Integration | Direction | Verification level |
|---|---|---|
| PyPI (`crewscore`) | Outbound publish | **Production-Verified.** 0.6.14 published by OIDC trusted publishing (run 38735565259), then installed and smoke-tested. |
| GitHub Pages (crewscore.ai) | Outbound deploy | Deployed at `16b9e36` (`pages-build-deployment` success); HTTP 200 for `/` and `/score-engine.js`. |
| GitHub Action `shmindmaster/crewscore@v2` | Consumed by other repos | Self-test passed at `16b9e36` (run 38736333626). `v2` moved to `v0.6.14` by the release. An external consumer repo was not exercised. |
| GitHub code scanning (SARIF) | Outbound, user-run | File format only. Upload is a documented step; not exercised. |
| Promptfoo and garak | Handoff | **Export only, not executed.** `export-eval` writes starter files; CrewScore never runs either tool. |
| PostHog (site analytics) | Outbound from browser | Present in `analytics.js`; production enablement and consent not checked. |
| arXiv:2606.15828 (smell definitions) | Reference | Cited in docs and code; not fetched here. |
| Pinned public prompt corpora | Inbound, at validation time | Fetched at pinned SHAs by `validate_corpus.py`; not run here. |

No model provider, database, payment, email or auth service is integrated.

## Gaps

**UI without backend.** The site has no backend by design: it runs the
generated engine locally. The share-link and analytics paths are client-side
only. Nothing found that is a UI element wired to nothing; the live page was
not exercised in this pass.

**Backend without UI.** Most of the product, by design: `scan`, `baseline`,
`init`, `export-eval`, `assess-vendor`, `--sarif`, `--report`, `--badge` and the
policy gate have no browser equivalent. `assess-vendor` and `export-eval` are
also secondary surfaces.

**Untested integrations (no executed evidence in this pack).**
- Promptfoo and garak: files are written, never run.
- SARIF upload to GitHub code scanning.
- The Action as consumed from `@v2` by an outside repo.
- PyPI publish from this workflow at 0.6.14.
- PostHog capture from the live site.

**Works locally only.**
- `scripts/validate_corpus.py` and the demo workspace builder (repo scripts,
  not in the wheel).
- The Playwright suite and `scripts/serve-static.mjs`.
- 0.6.14 itself: on main, not on PyPI.

**Known product gaps** (from [FUNCTIONAL.md](FUNCTIONAL.md#known-gaps)): no
runtime enforcement, thin construct validity for Cost, Compliance and Audit,
no MCP surface, no framework adapters.
