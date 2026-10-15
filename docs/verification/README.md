# CrewScore Verification Pack

Evidence pack for `shmindmaster/crewscore` at main `e9a1c9b` (package 0.6.14,
ruleset `crewscore-hygiene@0.6.0`). It records what exists, what was traced,
what was run, and what was shown. It does not repeat the product docs; it
links to them. The ladder used throughout is
Planned, Implemented, Integrated, Tested, Demonstrated, Production-Verified.

Facts that matter before reading further:

- PyPI publishes **0.6.14** (released 2026-10-15; its homepage is crewscore.ai). Main is `16b9e36`.
- Test evidence is in [TESTS.md](TESTS.md): the full suites ran on main's exact SHA, plus a smoke test of the published package.
  The verdict is in [READINESS.md](READINESS.md).
- The existing read-only assessment is reused, not rewritten:
  `AgentHub\runtime\coding-agent-dispatch\reports\showcase\crewscore.md`
  (2026-10-14, verdict ENHANCE_THEN_SHOWCASE).

## Purpose

CrewScore finds the written safeguards an agent system prompt never states:
a human-approval rule, an injection defense, a stop condition, a spend cap. It
is offline and deterministic (regex, no model). It reports **coverage** of 23
published controls in 8 dimensions. It does not measure whether the agent
obeys them. See [validation](../validation.md) and
[scoring and controls](../scoring-and-controls.md).

## Users

- AI platform and security engineers reviewing agent prompts.
- CI maintainers who want a gate on a named control rather than an average.
- Reviewers and consultants who need a cheap, reproducible, offline check.
- Visitors to crewscore.ai who paste a prompt and read the result in the
  browser, with scoring done locally in the page.

## What makes it different

- Honest by construction: the number is "N of 23 controls written", never a
  quality grade. Coding-agent config (`AGENTS.md`, `CLAUDE.md`, and so on)
  gets configuration smells and no governance score.
- Policy on controls, not averages: `--require human_gate.approval_required`.
- Prompt-free machine output (JSON, summary, SARIF and baselines carry control
  IDs, not prompt text).
- Published validation over 356 pinned public prompts, generated rather than
  typed. See [validation](../validation.md).
- Fail-closed discovery: links are never followed (`crewscore/pathsafe.py`).

## Capability inventory

| Capability | Entry point | Doc |
|---|---|---|
| Score a prompt | `crewscore test` | [cli](../cli.md) |
| Scan a repo | `crewscore scan` | [cli](../cli.md) |
| Plan or apply fixes | `crewscore fix` (`--plan` writes nothing) | [cli](../cli.md) |
| Print the open rule catalog | `crewscore rules` | [scoring](../scoring-and-controls.md) |
| Export live-eval starters | `crewscore export-eval` (writes Promptfoo and garak files; runs neither) | [next-steps-eval](../next-steps-eval.md) |
| Policy gate | `--require`, `--forbid-missing`, `--config` | [policies](../policies.md) |
| Baseline and regression | `crewscore baseline`, `--baseline --fail-on-regression` | [policies](../policies.md) |
| SARIF 2.1.0 (prompt-free) | `--sarif PATH` | [policies](../policies.md) |
| Policy scaffold | `crewscore init` | [policies](../policies.md) |
| HTML report and SVG badge | `test --report --badge` | [cli](../cli.md) |
| GitHub Action | `shmindmaster/crewscore@v2` (`action.yml`) | [github-action](../github-action.md) |
| Static browser checker | https://crewscore.ai/ (`index.html` + generated `score-engine.js`) | [architecture](../architecture.md) |
| Demo workspace builder | `python scripts/build_demo_workspace.py DIR` | [DEMOS](DEMOS.md) |
| Validation corpus | `scripts/validate_corpus.py` | [validation-corpus](../validation-corpus.md) |
| Vendor checklist (secondary, self-attest) | `crewscore assess-vendor` | [cli](../cli.md) |

## Pack contents

| File | What it holds |
|---|---|
| [README.md](README.md) | This page. |
| [FUNCTIONAL.md](FUNCTIONAL.md) | Roles, journeys with exact commands, business rules, errors, gaps. |
| [TECHNICAL.md](TECHNICAL.md) | Architecture diagram, data, secrets, CI/CD, debt, critical-feature trace. |
| [COVERAGE.md](COVERAGE.md) | Evidence matrix, integrations, and the gap lists. |
| [TESTS.md](TESTS.md) | Executed test commands and results. |
| [DEMOS.md](DEMOS.md) | Delivered films and traces. |
| [READINESS.md](READINESS.md) | Verdict, the three readiness types, next action. |

TESTS.md, DEMOS.md and READINESS.md are written separately from this file.
