CrewScore (0.6.1) is an offline, deterministic checker for AI agent system
prompts and coding-agent config (AGENTS.md smells).

What it is:
- 23 public written controls across 8 dimensions
- `crewscore scan .` + GitHub Action with control policies / SARIF
- Browser checker at https://crewscore.ai (prompt text stays local)

What it is not:
- CrewScore checks whether written guardrails are present in prompt text. It is not a red team, runtime enforcer, or safety certification.

Install:
```
pip install crewscore
crewscore scan .
```

Repo: https://github.com/shmindmaster/crewscore
Validation: https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md
