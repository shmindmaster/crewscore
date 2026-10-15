```yaml
product: CrewScore
repo: C:\Repos\shmindmaster\crewscore (github.com/shmindmaster/crewscore)
commit: 16b9e36c57cd6be410b2b3f59b95b7f42cae8029
verdict: Verified End-to-End Ready
functional_ready: yes
demo_ready: partial
production_ready: yes
deployed_sha: "PyPI 0.6.14 from 34214b1 (tag v0.6.14); crewscore.ai Pages at 16b9e36"
tests: "pytest: 676/678 (2 skipped) x py3.11/3.12/3.13 @ 16b9e36 run 38736329953; min-deps: 16/16 @ 16b9e36; browser E2E+axe: 211/232 (21 skipped) @ 16b9e36; selftest: pass @ 16b9e36 run 38736333626; release: 3-OS build+wheel smoke+publish pass @ 34214b1 run 38735565259; prod smoke: PyPI 0.6.14 exit 2 -> 0 pass 2026-10-15"
films: ["D:\\OneDrive - Maya Modest LLC\\Videos\\Portfolio\\CrewScore\\01 - One Sentence.mp4", "D:\\OneDrive - Maya Modest LLC\\Videos\\Evergreen\\Proof Clips\\03 - CrewScore Missing Safeguards.mp4"]
blockers: []
next_action: "Produce the C technical deep dive and the vertical short planned in DEMOS.md; then give the auto-merge controller a token whose pushes start workflows, so main is tested on every merge without a manual dispatch."
updated: 2026-10-15T13:10:00Z
```

# Readiness

**Verdict: Verified End-to-End Ready.** The scope is the CLI, the `--require` gate, the GitHub Action and the static checker.
- The core journey is proven at every rung, from the CLI argument to the exit code: score a prompt, require a named control, fail at exit 2, add the sentence, pass at exit 0.
- It is tested on main's exact SHA on three Python versions, demonstrated in a real recording, and production-verified against the package now on PyPI.

| Readiness | Rating | Why |
|---|---|---|
| Functional | **yes** | All CLI journeys in [FUNCTIONAL.md](FUNCTIONAL.md) have passing tests at `16b9e36` (676 pytest on 3.11–3.13). The browser checker passes 211 E2E and accessibility cases across Chromium, Firefox, WebKit and mobile. |
| Demo | **partial** | The hero film and the proof clip are real recordings on `e9a1c9b` (QA in [DEMOS.md](DEMOS.md)). The C deep dive and vertical short are planned, not made. The browser checker and a consumer-repo Action run are not filmed. |
| Production | **yes** | PyPI 0.6.14 was published by the trusted-publishing release (all three OS jobs green), then smoke-tested from PyPI in a clean venv: exit 2, then 0, with the covered line and the crewscore.ai link. crewscore.ai serves the 0.6.0 engine from Pages at `16b9e36`. |

## Evidence ladder for the core capability (`test --require human_gate.approval_required`)

| Rung | Evidence |
|---|---|
| Implemented | `crewscore/cli.py`, `policy.py`, `scorers/structural_analysis.py` at `16b9e36` |
| Integrated | Traced end to end, file:line by file:line, in [TECHNICAL.md](TECHNICAL.md#critical-feature-trace) |
| Tested | [pytest 38736329953](https://github.com/shmindmaster/crewscore/actions/runs/38736329953) at `16b9e36` (`test_policy_and_sarif.py`, `test_hero_sequence.py`, `test_demo_workspace.py`) |
| Demonstrated | `01 - One Sentence.mp4`, a real terminal run at `e9a1c9b` showing exit 2 then 0 |
| Production-Verified | PyPI 0.6.14 (release run 38735565259), smoke on 2026-10-15: exit 2 → 0 |

Per-capability rungs are in [COVERAGE.md](COVERAGE.md).

## Fixed during this verification
- **Main was not being tested after auto-merge.** Pushes made with `GITHUB_TOKEN` don't start workflows, so `e9a1c9b` and `ceda231` had no pytest or self-test run on main. [#79](https://github.com/shmindmaster/crewscore/pull/79) added `workflow_dispatch` plus a test that pins it. Main was then dispatched and is green at `16b9e36`.
- **PyPI lagged main** (0.6.13, with the old github.io homepage). The 0.6.14 release was published on 2026-10-15 after the README update in #77. It was released by the public-presence session: `cut-release-tag.yml` run 38735525380 created annotated tag `v0.6.14`, which peels to `34214b1`. It was verified here.

## Risks and known limits (disclosed, not blockers)
- **Coverage is not runtime proof.** The output says so on every run. Runtime enforcement and live adversarial testing are out of scope by design; `export-eval` hands off to Promptfoo and garak without running them.
- **Construct validity is thinner for three dimensions** (cost, compliance, audit). This is disclosed in the scoring docs.
- **The auto-merge token remains the root cause.** Until the controller uses a token whose pushes start workflows, main is tested by dispatch, not automatically. This is a secrets change.
- **No MCP surface and no framework adapters** (on the roadmap).

## Next highest-value action
1. Make the C deep dive "How CrewScore decides", then the vertical short. Both are planned in [DEMOS.md](DEMOS.md) and reuse r2 footage, with local narration.
2. Switch the auto-merge controller to a token whose merges start `push` workflows.
