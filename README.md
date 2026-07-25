<div align="center">

# agent-guard

### Structural production-readiness scorecard for AI agent system prompts

```
$ pip install -e .
$ agent-guard test --prompt "You are a helpful assistant that..."

  AGENT GUARD — Structural Production Readiness Report
  ====================================================

  Prompt Injection Resistance      [----------]   0/100  MISSING
  Hallucination Guardrails         [----------]   0/100  MISSING
  Source Citation Requirements     [----------]   0/100  MISSING
  Cost Runaway Protection          [----------]   0/100  MISSING
  Human-in-the-Loop Gates          [----------]   0/100  MISSING
  Safe-Stop Behavior               [----------]   0/100  MISSING
  Audit Trail & Provenance         [----------]   0/100  MISSING
  Compliance Readiness             [----------]   0/100  MISSING

  OVERALL SCORE:  0/100  NOT PRODUCTION READY
```

Score the **text** of your agent instructions. Fix gaps. Gate CI when scores drop.

[Install](#install) · [Usage](#usage) · [How scoring works](#how-scoring-works) · [CI](#ci-integration) · [Limits](#what-this-is-and-is-not)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)

</div>

---

## The problem

You shipped an agent that works in a demo. Before production you still need to ask:

- Does the prompt resist obvious injection / override language?
- Does it forbid fabricating citations and force “I don’t know”?
- Are writes, sends, and publishes gated on human approval?
- Is there any cost, audit, or compliance language at all?

Most teams never inspect those instructions systematically. **agent-guard** does a fast structural scan and can append proven guardrail patterns.

---

## What this is (and is not)

| Is | Is not |
|----|--------|
| Offline structural scan of system-prompt text | Live adversarial LLM red-teaming |
| Fix mode that appends guardrail sections | Proof that the runtime will obey the text |
| JSON output + exit threshold for CI | LangGraph / CrewAI graph execution analysis |
| Vendor checklist (`assess-vendor`) for procurement diligence | Independent security certification |

Scores reflect **prompt-text signals**. They are a useful smoke test, not a guarantee of runtime safety.

---

## Install

```bash
# from source (recommended while pre-PyPI)
pip install -e ".[dev]"

# or once published
pip install agent-guard
```

No API key for structural mode.

---

## Usage

### Score a system prompt

```bash
agent-guard test --prompt "You are a customer service agent for..."
agent-guard test --prompt-file ./my-agent/system-prompt.md
agent-guard test --prompt-file ./my-agent/system-prompt.md --json
agent-guard test --prompt-file ./my-agent/system-prompt.md --json --threshold 50
```

`--threshold N` exits with code `2` when overall score is below `N` (CI gate).

### Apply guardrail patterns

```bash
# print enhanced prompt
agent-guard fix --prompt-file ./system-prompt.md

# write in place and show score delta
agent-guard fix --prompt-file ./system-prompt.md --apply

# write to a new file
agent-guard fix --prompt-file ./system-prompt.md --output ./system-prompt-guarded.md

# machine-readable summary
agent-guard fix --prompt-file ./system-prompt.md --apply --json
```

### Score an AI vendor (checklist)

```bash
agent-guard assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y"
agent-guard assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json
```

Answers are `y` / `n` / `dk` for each of 10 diligence questions.

### Browser demo

Open `index.html` locally for a zero-install structural scan and vendor checklist UI (client-side only; not the CLI implementation).

---

## How scoring works

Eight dimensions, equal weight, each 0–100:

| Dimension | What the scanner looks for |
|-----------|----------------------------|
| Prompt Injection Resistance | Reject-override / do-not-reveal-system / jailbreak language |
| Hallucination Guardrails | No fabrication, “I don’t know”, grounded-only claims |
| Source Citation | Claims must cite sources / evidence |
| Cost Runaway Protection | Token/budget/max-length limits |
| Human-in-the-Loop Gates | Approval before send/write/publish |
| Safe-Stop Behavior | Halt when evidence missing or uncertain |
| Audit Trail | Log decisions / immutable trail language |
| Compliance Readiness | HIPAA/SOC2/GDPR/EU AI Act style handling language |

### Score tiers

| Score | Verdict |
|-------|---------|
| 90–100 | PRODUCTION READY (structurally) |
| 70–89 | SHIP WITH MONITORING |
| 50–69 | NEEDS WORK |
| 0–49 | NOT PRODUCTION READY |

---

## CI integration

```yaml
# .github/workflows/agent-safety.yml
name: Agent Safety Check
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install .
      - run: agent-guard test --prompt-file ./agents/system-prompt.md --json --threshold 50
```

Or parse JSON yourself:

```bash
SCORE=$(agent-guard test --prompt-file ./agents/system-prompt.md --json | jq '.overall')
```

---

## Fix patterns

When dimensions score below threshold, `agent-guard fix` appends production-style guardrail sections for:

- Injection defense
- Anti-hallucination
- Citation requirements
- Cost governance
- Human gates
- Safe-stop
- Audit trail
- Compliance / data protection

These are **prompt text templates**. Wire matching runtime controls (tool gates, logging, budgets) in your application.

---

## Development

```bash
git clone https://github.com/shmindmaster/agent-guard.git
cd agent-guard
pip install -e ".[dev]"
pytest
agent-guard test --prompt "You are a helpful assistant"
```

See [AGENTS.md](AGENTS.md) for agent/contributor operating notes.

---

## Roadmap (not implemented yet)

- Live adversarial testing against a real model endpoint
- Framework adapters that extract prompts from LangGraph / CrewAI / AutoGen graphs
- Hosted shareable HTML reports
- Official GitHub Action wrapper

---

## License

MIT.
