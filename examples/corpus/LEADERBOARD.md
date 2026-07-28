# CrewScore corpus leaderboard

Synthetic fixtures representing common agent-prompt shapes (bare demo → partial hygiene → hardened ops). **Structural scores only** — not red-team results, not runtime proof.

- **Ruleset:** `crewscore-hygiene@0.2.3`
- **Generated:** 2026-07-28
- **Command:** `crewscore scan examples/corpus`
- **Regenerate:** `python scripts/score_corpus.py`

| Rank | Path | Score | Tier |
| ---: | --- | ---: | --- |
| 1 | `prompts/05-hardened-ops.md` | **87** | `STRUCTURAL: OK WITH GAPS` |
| 2 | `prompts/04-partial-hygiene.md` | **20** | `STRUCTURAL: CRITICAL GAPS` |
| 3 | `prompts/03-agents-md-weak.md` | **0** | `STRUCTURAL: CRITICAL GAPS` |
| 4 | `prompts/02-demo-agent.md` | **0** | `STRUCTURAL: CRITICAL GAPS` |
| 5 | `prompts/01-bare-assistant.md` | **0** | `STRUCTURAL: CRITICAL GAPS` |

## How to reproduce

```bash
pip install crewscore
crewscore scan examples/corpus
crewscore scan examples/corpus --json
crewscore test --prompt-file examples/corpus/prompts/01-bare-assistant.md --explain
```

## Takeaway

Bare demo agents score near zero on production hygiene signals. Adding explicit injection/hallucination/human-gate language raises the structural score. That is a **pre-gate**, not certification — pair with Promptfoo/garak for live eval.

