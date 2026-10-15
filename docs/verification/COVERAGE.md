# Coverage matrix

One row per capability at main `e9a1c9b` (0.6.14). Rungs: Planned, Implemented,
Integrated, Tested, Demonstrated, Production-Verified.

How to read the rung column:

- **Implemented** means the code exists at the path shown (read, not run).
- **Integrated** means the path from entry point to visible result was traced
  in the code ([TECHNICAL.md](TECHNICAL.md#critical-feature-trace) for the
  main one). It was traced by reading, not by a live execution in this pass.
- **Tested** is decided only by [TESTS.md](TESTS.md). This pack ran no tests,
  so it claims no Tested rung. Test files below exist; whether they pass is
  "see TESTS.md". The last recorded pass in the repo is 639 Python tests at
  `d57a975` on 2026-09-09 ([current-state](../current-state.md)), which is a
  different commit.
- **Demonstrated** is claimed only where the delivered film shows it. The film
  `D:\OneDrive - Maya Modest LLC\Videos\Portfolio\CrewScore\01 - One Sentence.mp4`
  was recorded on `e9a1c9b`. It shows `test`, `fix --plan`, `test --require`
  failing then passing, and the `structural_analysis.py` human-gate code. See
  [DEMOS.md](DEMOS.md).
- **Production-Verified** needs a deployed SHA plus a health check and a smoke
  test of the path. None has that here; see the deploy column.

## Deploy facts observed

| Item | Observed |
|---|---|
| PyPI `crewscore` | 0.6.13 published (PyPI JSON, this pass). Its Homepage is still `https://shmindmaster.github.io/crewscore/`. Main is 0.6.14, unreleased. |
| crewscore.ai | `HTTP/1.1 200 OK`, `Server: GitHub.com`, `Last-Modified: Wed, 14 Oct 2026 14:40:50 GMT`. Deployed commit: not checked. |
| Action tag `v2` | GitHub API lists `refs/tags/v2` as an annotated tag object `06d19e9`. The commit it peels to was not resolved. The local clone's `v2` points at `9ee82ce`; the local ref may be stale. No `v0.6.14` tag exists locally; remote not checked. |
| Pages source | `main`, repository root, `CNAME` `crewscore.ai` (from [current-state](../current-state.md); no Pages workflow in the repo) |

## Evidence matrix

Surface: CLI, Action (A), or site (S). Test column lists files that exist in
`tests/` (or `web-tests/`) for the capability, not results.

| Capability | Journey | Surface | Logic module | Integration | Test files | Test run | Demo | Deploy status | Rung evidenced |
|---|---|---|---|---|---|---|---|---|---|
| `test` (score a prompt) | [FUNCTIONAL #1-2](FUNCTIONAL.md) | CLI | `crewscore/cli.py:338`, `scorers/structural_analysis.py:715`, `scoring.py:133` | Traced end to end in [TECHNICAL](TECHNICAL.md#critical-feature-trace) | `tests/test_cli.py`, `test_concept_scoring.py`, `test_structural_analysis.py`, `test_viral_wedge_cli.py`, `test_hero.py`, `test_hero_sequence.py` | see TESTS.md | see DEMOS.md (shown in film) | PyPI 0.6.13 has the capability; 0.6.14 unreleased | Demonstrated |
| `--require` policy gate | #3, #5 | CLI, A | `crewscore/policy.py:168,262` | Same trace, hops 3, 5, 11, 14 | `tests/test_policy_and_sarif.py`, `test_hero_sequence.py`, `test_demo_workspace.py` | see TESTS.md | see DEMOS.md (exit 2 then 0 in film) | PyPI 0.6.13: pass line added in 0.6.13 per commit ad8cd88 subject, not re-checked | Demonstrated |
| `fix` (plan, apply, output) | #7-8 | CLI | `cli.py:1009`, `scorers/fix_patterns.py` | Read; `--plan` path not traced line by line | `tests/test_cli.py`, `test_demo_workspace.py` | see TESTS.md | see DEMOS.md (`fix --plan` in film; `--apply` not shown) | As above | Demonstrated (`--plan` only); Implemented (`--apply`) |
| `scan` (repo discovery, contained) | #4-6 | CLI, A | `crewscore/scan.py:151`, `pathsafe.py`, `cli.py:1556` | Read, not traced | `tests/test_scan.py`, `test_scan_containment.py`, `test_redos.py`, `test_extract_inline.py` | see TESTS.md | Not shown in the film | As above | Implemented |
| `rules` (open catalog) | #9 | CLI | `crewscore/rules_catalog.py`, `cli.py:795` | Read | `tests/test_rules_catalog.py`, `test_scan.py` | see TESTS.md | Not shown | As above | Implemented |
| `export-eval` (Promptfoo and garak starters) | #13 | CLI | `crewscore/export_eval.py:355` | Writes files only; no tool is run | `tests/test_export_eval.py` | see TESTS.md | Not shown | As above | Implemented |
| Baseline and regression | #11-12 | CLI, A | `policy.py:309` (`baseline_payload`), `cli.py:1342` | Read | `tests/test_policy_and_sarif.py` | see TESTS.md | Not shown | As above | Implemented |
| SARIF 2.1.0 (prompt-free) | #4, #15 | CLI, A | `crewscore/sarif.py:45` | Read; upload to code scanning is a user step, not run here | `tests/test_policy_and_sarif.py`, `test_prompt_free_outputs.py` | see TESTS.md | Not shown | As above | Implemented |
| `init` scaffold | #10 | CLI | `cli.py:1380` | Read | `tests/test_hero_sequence.py`, `test_policy_and_sarif.py` (incidental) | see TESTS.md | Not shown | As above | Implemented |
| HTML report and SVG badge | #1 | CLI | `crewscore/report.py` | Read | `tests/test_report.py` | see TESTS.md | Not shown | As above | Implemented |
| PR/job markdown summary | #4, #15 | CLI, A | `crewscore/summary.py` | Read | `tests/test_summary.py`, `test_prompt_free_outputs.py` | see TESTS.md | Not shown | As above | Implemented |
| Prompt-free output gate | all | CLI, A | `crewscore/findings_export.py:27` | Read | `tests/test_prompt_free_outputs.py` (also run at dependency floors in `pytest.yml`) | see TESTS.md | Not shown | As above | Implemented |
| Coding-agent config path (smells, no score) | #6 | CLI | `profiles.py:74`, `smells.py`, `scoring.py:68` | Read | `tests/test_profiles.py`, `test_smells.py` | see TESTS.md | Not shown | As above | Implemented |
| GitHub Action | #15 | A | `action.yml` | Self-test workflow `crewscore-selftest.yml` exercises the local action in CI; its runs were not checked | `tests/test_action_manifest.py`, `test_workflow_*.py`; workflow `crewscore-selftest.yml` | see TESTS.md | Not shown | Tag `v2` exists remotely (see above); consumer-side run not checked | Implemented, Integrated by CI design (run history not checked) |
| Static browser checker | #16 | S | `crewscore/web_export.py:446,514` -> `score-engine.js` -> `index.html` | Generation boundary traced; page behavior not run here | `tests/test_web_engine.py`, `test_web_ux.py`; `web-tests/checker.spec.mjs` (58 `test(` calls by static count) | see TESTS.md | Not shown in the film | crewscore.ai HTTP 200, Last-Modified 2026-10-14 14:40:50 GMT; deployed SHA not checked | Implemented |
| `score-engine.js` parity | all site use | S | `scripts/export_web_engine.py` | Release gate regenerates and diffs it (`release.yml`) | `tests/test_web_engine.py` | see TESTS.md | Not shown | Same as site | Implemented |
| Demo workspace builder | #17 | CLI | `scripts/build_demo_workspace.py` | Read | `tests/test_demo_workspace.py` | see TESTS.md | see DEMOS.md (the film's fixture path) | Repo only, not packaged | Implemented |
| Validation corpus and stats | #18 | CLI script | `scripts/validate_corpus.py` | Needs network to fetch pinned SHAs; not run | `tests/test_corpus.py`, `test_corpus_harness.py`, `test_corpus_scores.py`, `test_published_numbers.py` | see TESTS.md | Not shown | Published docs: `docs/validation-corpus.md` | Implemented |
| Vendor checklist | #14 | CLI | `crewscore/vendor_scorecard.py` | Read | `tests/test_vendor.py` | see TESTS.md | Not shown | As above | Implemented |
| Metrics schema and site analytics | site | S | `crewscore/metrics.py`, `analytics.js` | Not traced; endpoint is PostHog (`analytics.js:5`) | `tests/test_metrics.py`, `test_analytics_claims.py` | see TESTS.md | Not shown | Enablement in production not checked | Implemented |
| PyPI release pipeline | n/a | CI | `.github/workflows/release.yml`, `cut-release-tag.yml`, `scripts/cut_release.py` | Trusted publishing (OIDC) read in workflow | `tests/test_release_automation.py`, `test_workflow_provenance.py`, `test_packaging_contract.py` | see TESTS.md | n/a | 0.6.13 on PyPI; whether it came through this workflow was not checked | Implemented |

No capability reaches Production-Verified in this pack. For the CLI, that
needs a fresh install of the released package and the demo path run against it;
for the site, the deployed SHA and a smoke run of the checker.

## Integrations

| Integration | Direction | Verification level |
|---|---|---|
| PyPI (`crewscore`) | Outbound publish | 0.6.13 present on PyPI (observed). Trusted-publishing config in workflow read; PyPI-side registration and the publish run itself not checked. Main is ahead (0.6.14). |
| GitHub Pages (crewscore.ai) | Outbound deploy | HTTP 200 observed. Source is `main` root. Deployed SHA not checked. |
| GitHub Action `shmindmaster/crewscore@v2` | Consumed by other repos | Tag exists remotely (peeled commit not resolved). Self-tested in CI by workflow design; run results and any external consumer not checked. |
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
