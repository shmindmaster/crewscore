# Corpus demo (structural)

Honest, **synthetic** agent-prompt fixtures for demos and regression checks.

These are not scraped third-party system prompts (copyright/attribution risk).
They represent shapes teams actually ship: bare assistants, sales demos,
weak `AGENTS.md`, partial hygiene, and a hardened ops example.

## Score it

```bash
crewscore scan examples/corpus
python scripts/score_corpus.py   # refreshes LEADERBOARD.md
```

## What this proves

| Intent | Fixture |
|--------|---------|
| Zero-friction bare prompt fails the gate | `prompts/01-bare-assistant.md` |
| Demo agents still lack production signals | `prompts/02-demo-agent.md` |
| Repo agent docs ≠ hygiene (coding-agent config, judged on configuration smells, not a governance score) | `repo-config/AGENTS.md` |
| A few real rules move the needle | `prompts/04-partial-hygiene.md` |
| Text can look “strong” structurally | `prompts/05-hardened-ops.md` |

Scores are **structural** (regex ruleset). High text coverage ≠ runtime safety.
See [LEADERBOARD.md](./LEADERBOARD.md) and `docs/next-steps-eval.md`.
