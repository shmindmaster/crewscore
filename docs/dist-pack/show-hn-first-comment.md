CrewScore is offline CI for **missing written guardrails** in AI agent system
prompts (and configuration smells for AGENTS.md).

What it is:
- 23 public written controls; output is **control coverage N/23**, not a quality rank
- Hero gap + one-control CI: `crewscore scan . --require human_gate.approval_required`
- Finds `SYSTEM_PROMPT = """..."""` in .py/.ts/.js as well as prompt files
- GitHub Action + SARIF; browser checker at https://crewscore.ai

What it is not:
- Not a red team, runtime enforcer, or safety certification — text presence only

Shock number (reproducible corpus): production-agent median coverage **10/100**;
GPT-Store median **0**. Card: docs/dist-pack/corpus-card.svg

Install:
```
pip install crewscore
crewscore scan .
```

Repo: https://github.com/shmindmaster/crewscore
Validation: https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md
