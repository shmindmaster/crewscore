# Where CrewScore sits

## Other static linters for agent instruction files

CrewScore is not the only one, and pretending otherwise would be the fastest
way to lose your trust.

| Tool | What it asks | Where it differs |
|------|--------------|------------------|
| [AgentLinter](https://github.com/seojoonkim/agentlinter) | *"Will this file make the coding agent work well?"* | npm / `npx`, weighted dimensions, cross-file contradiction detection across a workspace |
| [lintlang](https://github.com/hermes-labs-ai/lintlang) | Static gating for agent configs | Zero-LLM CI linting |
| **CrewScore** | *"Will this agent hurt someone in production?"* | Governance lens — injection, human gates, audit, compliance — plus offline detection of published configuration smells |

If you want agent-config *craft* — clarity, structure, memory layout —
AgentLinter is aimed squarely at that and is worth your time. CrewScore's lens
is production governance. They are complementary, and running both is
reasonable.

---

## After CrewScore

CrewScore is the cheap structural pre-gate. When you need **live** behaviour:

| Need | Tool |
|------|------|
| Prompt eval suites, YAML scenarios, CI assertions | [Promptfoo](https://www.promptfoo.dev/) |
| LLM vulnerability / jailbreak scanning | [garak](https://github.com/NVIDIA/garak) (NVIDIA) |
| Deeper agent red-team | Promptfoo agents, PyRIT, or your own harness |

A structural score does **not** measure jailbreak resistance or multi-turn tool
abuse. Use those tools once the prompt text has basic hygiene.

Generate starter stubs (this does **not** run live evals):

```bash
crewscore export-eval --prompt-file ./agents/system-prompt.md -o ./crewscore-eval
# -> promptfooconfig.yaml + README-EVAL.md
```

Details: [next-steps-eval.md](next-steps-eval.md).

---

## Name note

The PyPI package `agent-guard` is an unrelated third-party CrewAI monitoring
library. This project is **CrewScore** (`pip install crewscore`). The CLI also
accepts the legacy alias `agent-guard` after install.
