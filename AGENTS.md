# CrewScore — agent instructions

## What this is

Offline CLI that **structurally** scores AI agent system prompts for production-readiness signals (injection defense, hallucination policy, citations, cost limits, human gates, safe-stop, audit, compliance), applies fix patterns, and runs a non-technical AI vendor checklist.

Public brand: **CrewScore** · Domain: **https://crewscore.ai** · PyPI: **`crewscore`** · Repo: **shmindmaster/crewscore**

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
crewscore test --prompt "You are a helpful assistant..."
crewscore test --prompt-file ./system-prompt.md --explain
crewscore test --prompt-file ./system-prompt.md --json --explain
crewscore test --prompt-file ./system-prompt.md --json --threshold 50
crewscore test --prompt-file ./system-prompt.md --report out.html --badge badge.svg

# apply guardrail patterns
crewscore fix --prompt-file ./system-prompt.md
crewscore fix --prompt-file ./system-prompt.md --apply
crewscore fix --prompt-file ./system-prompt.md --output ./guarded.md --json

# vendor checklist
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json

# after pattern changes: keep web in lockstep
python scripts/export_web_engine.py

# tests
pytest
```

Legacy CLI entry point `agent-guard` still maps to the same `crewscore.cli:main` after install.

## Layout

```
crewscore/
  cli.py                 # click entry (test, fix)
  scoring.py             # shared result model / tiers
  vendor_scorecard.py    # assess-vendor command
  web_export.py          # builds score-engine.js payload
  report.py              # HTML report + SVG badge
  scorers/
    structural_analysis.py
    fix_patterns.py
scripts/export_web_engine.py
score-engine.js          # generated — commit after pattern changes
index.html               # dual-tab site (uses score-engine.js)
action.yml               # composite GH Action
docs/launch/             # launch copy kit
tests/
```

## Product constraints

- Prefer honest capability claims over roadmap theater.
- Structural scores are pattern matches on prompt text, not proof of runtime behavior.
- Keep the package dependency-light (no LLM SDKs required for the core path).
- Fame follows usefulness: explainable findings, fix, CI gate before launch theater.
- Breaking CLI flags are acceptable if all docs and tests update in the same change.
- Never document `pip install agent-guard` as *this* product (that PyPI name is taken by another package).

## Do not

- Reintroduce fake `--langgraph` / `--crewai` loaders or adversarial mode stubs without real implementations.
- Link to non-existent report hosts or wrong GitHub/PyPI names.
- Add empty `examples/` / `evaluator/` / `patterns/` directories without content.
- Overclaim “production safety certification” or “7 regulated systems” beyond structural scanning.
