# agent-guard — agent instructions

## What this is

Offline CLI that **structurally** scores AI agent system prompts for production-readiness signals (injection defense, hallucination policy, citations, cost limits, human gates, safe-stop, audit, compliance), applies fix patterns, and runs a non-technical AI vendor checklist.

It does **not** (yet) run live adversarial LLM attacks or parse LangGraph/CrewAI runtimes.

## Stack

- Python 3.11+
- click + rich
- hatchling packaging
- pytest

## Commands

```bash
# install (editable)
pip install -e ".[dev]"

# score a prompt
agent-guard test --prompt "You are a helpful assistant..."
agent-guard test --prompt-file ./system-prompt.md
agent-guard test --prompt-file ./system-prompt.md --json
agent-guard test --prompt-file ./system-prompt.md --json --threshold 50

# apply guardrail patterns
agent-guard fix --prompt-file ./system-prompt.md
agent-guard fix --prompt-file ./system-prompt.md --apply
agent-guard fix --prompt-file ./system-prompt.md --output ./guarded.md --json

# vendor checklist
agent-guard assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json

# tests
pytest
```

## Layout

```
agent_guard/
  cli.py                 # click entry (test, fix)
  scoring.py             # shared result model / tiers
  vendor_scorecard.py    # assess-vendor command
  scorers/
    structural_analysis.py
    fix_patterns.py
tests/
index.html               # static browser demo (client-side structural scan)
```

## Product constraints

- Prefer honest capability claims over roadmap theater.
- Structural scores are pattern matches on prompt text, not proof of runtime behavior.
- Keep the package dependency-light (no LLM SDKs required for the core path).
- Breaking CLI flags are acceptable if all docs and tests update in the same change.

## Do not

- Reintroduce fake `--langgraph` / `--crewai` loaders or adversarial mode stubs without real implementations.
- Link to non-existent report hosts or wrong GitHub repo names.
- Add empty `examples/` / `evaluator/` / `patterns/` directories without content.
