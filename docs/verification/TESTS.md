# Tests

Every result below was executed and is linked to its run. Hosted runs are on ephemeral GitHub-hosted runners. Main is `16b9e36` (#79), and the package is 0.6.14.

## Main, at its exact SHA

Dispatched on 2026-10-15 against `16b9e36c57cd6be410b2b3f59b95b7f42cae8029`.

| Suite | Command (from the workflow) | Environment | Result | Run |
|---|---|---|---|---|
| Unit, contract and CLI tests | `pip install -e ".[dev]"`, then `pytest -q` | ubuntu-latest, Python 3.11 | **676 passed, 2 skipped** | [pytest 38736329953](https://github.com/shmindmaster/crewscore/actions/runs/38736329953) |
| Same | Same | Python 3.12 | **676 passed, 2 skipped** | same run |
| Same | Same | Python 3.13 | **676 passed, 2 skipped** | same run |
| Minimum supported dependencies (CLI privacy contracts at the dependency floors) | `pytest -q tests/test_prompt_free_outputs.py` at the minimum pins | ubuntu-latest | **16 passed** | same run |
| Runtime dependency audit | the audit job added in #78 | ubuntu-latest | **pass** | same run |
| Browser checker E2E plus accessibility (Playwright 1.63 and axe-core) | `npm ci`, `npm run test:automerge`, `npx playwright install --with-deps chromium firefox webkit`, `npm run test:web` | Chromium, Firefox, WebKit and mobile projects | **211 passed, 21 skipped** | same run |
| Action self-test (the local `action.yml` scoring this repo) | `crewscore-selftest.yml` | ubuntu-latest | **pass** | [CrewScore Self-Test 38736333626](https://github.com/shmindmaster/crewscore/actions/runs/38736333626) |

The 2 pytest skips and 21 browser skips are explicit skips in the suites, not failures. docs/current-state.md records the same 21 browser skips.

## Release pipeline (0.6.14)

| Check | Result | Run |
|---|---|---|
| Release tag preconditions, dry run (`cut-release-tag.yml`, `push=false`) on `e9a1c9b` | pass | [38706031459](https://github.com/shmindmaster/crewscore/actions/runs/38706031459) |
| Release on `34214b1`: test, build and verify the artifacts on Linux, macOS and Windows; smoke-test the built wheel in a clean environment; publish to PyPI (OIDC trusted publishing); create the GitHub release; move the floating major tag | all jobs pass | [Release 38735565259](https://github.com/shmindmaster/crewscore/actions/runs/38735565259) |

## Production smoke checks (2026-10-15, after publish)

| Check | Result |
|---|---|
| `pip install crewscore==0.6.14` into a clean venv; `crewscore --version` | `crewscore, version 0.6.14` |
| `crewscore test -f p.md --no-explain --require human_gate.approval_required` on a one-line prompt | exit **2** (required control missing) |
| Same, after adding "A human must approve any refund before it happens." | exit **0**, prints `REQUIRED CONTROL COVERED: human_gate.approval_required (the text states it; not proof the agent obeys it)` and `https://crewscore.ai/` |
| PyPI JSON | version 0.6.14, Homepage `https://crewscore.ai/` |
| `https://crewscore.ai/` and `/score-engine.js` | HTTP 200 for both; the engine carries `crewscore-hygiene@0.6.0` |
| Pages deployment | `pages-build-deployment` succeeded on `16b9e36` |

## Local runs

| Command | Commit | Result |
|---|---|---|
| `pytest -q tests/test_workflow_runner_policy.py` (Windows, Python 3.13) | #79 branch | 10 passed |
| The film's terminal runs: `test`, `fix --plan`, `test --require` before and after the sentence (Windows, Git Bash, clean venv) | `e9a1c9b` | exit 0, 0, 2 then 0; full output in the film's `receipts/terminal-commands.jsonl` (see [DEMOS.md](DEMOS.md)) |

## What the suites cover

The Python suite covers:
- scoring, the 23-control concept map, `--require` policy, SARIF, baselines and regression, prompt-free output;
- scan containment (`pathsafe`, ReDoS), profiles and smells;
- `fix`, `export-eval`, `init`, report and badge, the vendor checklist, metrics;
- the corpus numbers (`test_published_numbers.py` fails if the published report drifts from a fresh run);
- parity between the Python engine and `score-engine.js` (`test_web_engine.py`);
- workflow and Action contracts.

The browser suite drives the static checker end to end, including the keyboard path, axe accessibility, dark and light themes, and mobile width.

## Not covered by any executed run
- Live adversarial or LLM evaluation. This is out of scope by design: `export-eval` only writes starter configs.
- The Action running inside a third-party consumer repository. `example-ci.yml` exists, but no run was dispatched for this pack.
- Network fetch of the validation corpus at its pinned SHAs (`scripts/validate_corpus.py`). The committed report is guarded by `test_published_numbers.py`.

## Gap found and fixed while assembling this file
Auto-merge pushes to main with `GITHUB_TOKEN`, so `push: main` never started `pytest` or the self-test after an auto-merged PR. Main commits `e9a1c9b` and `ceda231` had no test run of their own. [#79](https://github.com/shmindmaster/crewscore/pull/79) added `workflow_dispatch` (pinned by `tests/test_workflow_runner_policy.py`), and the runs above were dispatched on main afterwards. The remaining root cause is that the auto-merge token's pushes don't start workflows; see [READINESS.md](READINESS.md).
