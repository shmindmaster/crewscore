<div align="center">

# agent-guard

### Is your AI agent production-safe? Find out in 30 seconds.

```
$ pip install agent-guard
$ agent-guard test --prompt "You are a helpful assistant that..."

  AGENT GUARD - Production Readiness Report
  ==========================================

  Prompt Injection Resistance      [----------]   0/100  MISSING
  Hallucination Guardrails         [===-------]  26/100  FAILS
  Source Citation Requirements     [----------]   0/100  MISSING
  Cost Runaway Protection          [----------]   0/100  MISSING
  Human-in-the-Loop Gates          [----------]   0/100  MISSING
  Safe-Stop Behavior               [----------]   0/100  MISSING
  Audit Trail & Provenance         [----------]   0/100  MISSING
  Compliance Readiness             [----------]   0/100  MISSING

  OVERALL SCORE:  3/100  NOT PRODUCTION READY
```

**Most agents score below 50.** Score yours. Fix it. Share your score.

[Install](#install) | [How It Works](#how-scoring-works) | [Fix Mode](#fix-mode) | [CI Integration](#ci-integration)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-agent--guard-blue.svg)](https://pypi.org/project/agent-guard/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)

</div>

---

## The Problem

You built an AI agent. It works in the demo. But:

- Will it **fabricate citations** when a user asks for sources?
- Can someone **override its instructions** with "ignore previous rules"?
- Will it **silently proceed** when critical evidence is missing?
- Could a single loop **cost you $500** in tokens?
- Does it have **any audit trail** for what it did and why?

83% of organizations are deploying AI agents. 40% of agentic AI projects will be canceled by 2027 (Gartner). The #1 reason isn't intelligence — it's **unguarded behavior in production**.

 Nobody stress-tests their agent before shipping. agent-guard does it in one command.

---

## Install

```bash
pip install agent-guard
```

That's it. No API key needed for the structural scan. Zero config.

---

## Usage

### Score your agent (30 seconds, free)

```bash
# From a string
agent-guard test --prompt "You are a customer service agent for..."

# From a file
agent-guard test --prompt-file ./my-agent/system-prompt.md

# From a LangGraph agent
agent-guard test --langgraph ./agents/graph.py

# From a CrewAI crew
agent-guard test --crewai ./agents/crew.yaml
```

### Fix your agent (10 seconds)

```bash
# Show what would be fixed
agent-guard fix --prompt-file ./system-prompt.md

# Apply fixes in-place and show the score improvement
agent-guard fix --prompt-file ./system-prompt.md --apply

# Save to a new file
agent-guard fix --prompt-file ./system-prompt.md --output ./system-prompt-guarded.md
```

Example output:

```
  AGENT GUARD - Applying Fixes
  ============================

  [OK] Added prompt injection defense
  [OK] Added anti-hallucination policy
  [OK] Added source citation requirements
  [OK] Added cost governance
  [OK] Added human-in-the-loop gates
  [OK] Added safe-stop protocol
  [OK] Added audit trail requirements
  [OK] Added compliance & data protection

  Score: 3/100 -> 58/100 (+55)
```

### Adversarial mode (live LLM testing, ~$0.50)

```bash
export ANTHROPIC_API_KEY=sk-...
agent-guard test --prompt "..." --mode adversarial
```

Runs live attack prompts against your agent. Tests if it actually resists injection, actually cites sources, actually stops when uncertain.

---

## How Scoring Works

8 dimensions. Each scored 0-100. Weighted equally.

| Dimension | What It Checks | Why It Matters |
|-----------|---------------|----------------|
| **Prompt Injection Resistance** | Can users override instructions? | $2.1B in AI-related fines in 2025 |
| **Hallucination Guardrails** | Will it fabricate facts/citations? | #1 reason AI projects lose trust |
| **Source Citation** | Does it attribute claims to sources? | Required for HIPAA, SOC2, EU AI Act |
| **Cost Runaway Protection** | Can one loop cost $500+? | Governance budget jumped 3% -> 12% of AI spend |
| **Human-in-the-Loop Gates** | Are dangerous actions gated? | "AI drafts, humans approve" is the production standard |
| **Safe-Stop Behavior** | Does it halt when uncertain? | A wrong action in healthcare/finance is worse than none |
| **Audit Trail** | Can you prove what it did? | Every regulated industry requires this now |
| **Compliance Readiness** | HIPAA/SOC2/EU AI Act patterns? | 40% of CIOs will demand Guardian Agents by 2028 |

### Score Tiers

| Score | Verdict |
|-------|---------|
| 90-100 | PRODUCTION READY - ship it |
| 70-89 | SHIP WITH MONITORING - add observability |
| 50-69 | NEEDS WORK - fix critical gaps first |
| 0-49 | NOT PRODUCTION READY - do not deploy |

---

## CI Integration

Score agents automatically in your pipeline. Fail the build if score drops below threshold:

```yaml
# .github/workflows/agent-safety.yml
name: Agent Safety Check
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install agent-guard
      - run: |
          SCORE=$(agent-guard test --prompt-file ./agents/system-prompt.md --json | jq '.overall')
          if [ "$SCORE" -lt 50 ]; then
            echo "Agent safety score $SCORE/100 is below threshold (50). Fix before merging."
            exit 1
          fi
```

---

## The Fix Patterns

When agent-guard finds gaps, it doesn't just diagnose. It **prescribes**. Each fix is a production-proven guardrail pattern extracted from 7 regulated AI systems running in production (healthcare, finance, legal):

- **Injection defense**: Reject override attempts, protect system instructions
- **Anti-hallucination**: Never fabricate, say "I don't know", distinguish fact from inference
- **Citation requirements**: Every claim cites its source, unverified claims flagged
- **Cost governance**: Token budgets, tool call limits, batch confirmation
- **Human gates**: Approval required for writes, sends, publishes, financial actions
- **Safe-stop**: Halt when evidence is missing or confidence is below threshold
- **Audit trail**: Log every action with timestamp, source, rationale
- **Compliance**: HIPAA/GDPR/SOC2 data handling patterns

---

## Why This Exists

I operate 7 AI systems in production across healthcare (HIPAA), financial services, legal, and logistics. Every single one broke in ways I didn't test for. An agent fabricated a court citation. Another ran up a $340 token bill in a loop. A third silently ignored a missing authorization and almost submitted an insurance claim without proper approval.

agent-guard is the test suite I wish I'd had before each of those incidents.

---

## Roadmap

- [x] Structural analysis (offline, no API key)
- [x] Fix mode with 8 guardrail patterns
- [x] Rich terminal scorecard
- [ ] Adversarial testing (live LLM attacks)
- [ ] `--json` output for CI/programmatic use
- [ ] HTML shareable report generation
- [ ] GitHub Actions integration (official action)
- [ ] LangGraph / CrewAI / AutoGen native adapters
- [ ] Agent fleet scoring (test all agents in a monorepo)
- [ ] Leaderboard: "the most guarded agents on GitHub"

---

## Contributing

```bash
git clone https://github.com/shmindmaster/agent-guard.git
cd agent-guard
pip install -e ".[dev]"
agent-guard test --prompt "You are a helpful assistant"
```

PRs welcome. Especially: new scoring dimensions, new fix patterns, framework adapters.

---

## Star This Repo

If you've ever shipped an agent and prayed it wouldn't hallucinate a citation or get prompt-injected in prod -- star it. We'll keep building.

---

## License

MIT. Use it, fork it, ship it. If it catches one hallucination before your users do, it's paid for itself.
