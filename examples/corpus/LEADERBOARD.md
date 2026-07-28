# CrewScore corpus leaderboard

Synthetic fixtures representing common agent-prompt shapes (bare demo → partial hygiene → hardened ops). **Structural scores only** — not red-team results, not runtime proof.

> **These are fixtures, not evidence.** They were written to exercise the rules, which is why the top one scores well. Across 1,368 real system prompts, nothing scored above 50/100 and the score did not separate production prompts from amateur ones once length was controlled. Read [`docs/validation.md`](../../docs/validation.md) before reading anything into a number here.

- **Ruleset:** `crewscore-hygiene@0.4.0`
- **Generated:** 2026-07-28
- **Command:** `crewscore scan examples/corpus`
- **Regenerate:** `python scripts/score_corpus.py`

| Rank | Path | Score | Tier |
| ---: | --- | ---: | --- |
| 1 | `prompts/05-hardened-ops.md` | **87** | `STRUCTURAL: OK WITH GAPS` |
| 2 | `prompts/04-partial-hygiene.md` | **20** | `STRUCTURAL: CRITICAL GAPS` |
| 3 | `prompts/02-demo-agent.md` | **0** | `STRUCTURAL: CRITICAL GAPS` |
| 4 | `prompts/01-bare-assistant.md` | **0** | `STRUCTURAL: CRITICAL GAPS` |

### Coding-agent config (no governance grade)

These files are repo guidance for a coding agent, not a production system prompt — they are judged on configuration smells, never the governance score. See [configuration smells](../../README.md#configuration-smells).

| Path | Verdict |
| --- | --- |
| `repo-config/AGENTS.md` | `CONFIG: NO SMELLS DETECTED` |

## How to reproduce

```bash
pip install crewscore
crewscore scan examples/corpus
crewscore scan examples/corpus --json
crewscore test --prompt-file examples/corpus/prompts/01-bare-assistant.md --explain
```

## Takeaway

Bare demo agents score near zero on production hygiene signals. Adding explicit injection/hallucination/human-gate language raises the structural score. That is a **pre-gate**, not certification — pair with Promptfoo/garak for live eval.

