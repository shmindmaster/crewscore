<div align="center">

# 🛡️ agent-guard

### Stress-test your AI agent. Get a production-readiness scorecard in 30 seconds.

**Does your agent halt when it should? Cite its sources? Have cost controls? Pass a prompt injection attack?**

Most agents score below 50. Find out yours.

```bash
pip install agent-guard
agent-guard test --prompt "You are a helpful healthcare assistant..."
```

[⚡ Quick Start](#-quick-start) · [📊 How Scoring Works](#-how-scoring-works) · [🔧 Fix Patterns](#-fix-patterns) · [🌍 Multi-Model](#-multi-model-support)

![agent-guard](https://img.shields.io/badge/status-pre--alpha-orange) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)

</div>

---

## The Problem

83% of organizations plan to deploy AI agents. Only 23% are actually scaling them. **40% of agentic AI projects will be canceled by 2027** (Gartner). The #1 reason isn't intelligence — it's that agents break in ways nobody tested for.

Everyone is building agents. Almost nobody is stress-testing them.

## The Fix

`agent-guard` runs 8 categories of adversarial and behavioral tests against any AI agent — from a system prompt string to a full LangGraph/CrewAI deployment — and produces a shareable production-readiness scorecard.

```
$ agent-guard test --prompt "You are a helpful assistant for a pharmacy chain..."

  🛡️  AGENT GUARD — Production Readiness Report
  ═══════════════════════════════════════════════════════

  Prompt Injection Resistance    ████████░░  80/100
  Hallucination Guardrails       ███░░░░░░░  31/100  ⚠️ FAILS
  Source Citation Requirements   ██████░░░░  62/100
  Cost Runaway Protection        ░░░░░░░░░░   0/100  ⚠️ MISSING
  Human-in-the-Loop Gates        ██░░░░░░░░  18/100  ⚠️ WEAK
  Safe-Stop Behavior             █████████░  91/100  ✓ PASS
  Audit Trail & Provenance       ░░░░░░░░░░   0/100  ⚠️ MISSING
  Compliance Readiness           █████░░░░░  48/100

  ─────────────────────────────────────────────────────
  OVERALL SCORE:  41/100  🔴 NOT PRODUCTION READY
  ─────────────────────────────────────────────────────

  ⚠️  CRITICAL:  Your agent will fabricate citations and has
      no cost ceiling. A single runaway loop could cost $500+.

  → Run  agent-guard fix  to apply recommended patterns.
  → Share  https://agent-guard.dev/r/a1b2c3

  Built by the team that operates 7 regulated AI systems → pendoah.ai
```

**That scorecard is shareable.** Post it. Brag about it. Or, more likely, fix your agent and post the improved score.

---

## ⚡ Quick Start

### 30-Second Test (No API Key Needed)

Paste your system prompt. Agent-guard runs structural analysis offline — no LLM calls, no cost.

```bash
pip install agent-guard

# Test from a string
agent-guard test --prompt "You are a helpful assistant..."

# Test from a file
agent-guard test --prompt-file ./my-agent/system-prompt.md

# Test a LangGraph agent
agent-guard test --langgraph ./my-agent/graph.py

# Test a CrewAI crew
agent-guard test --crewai ./my-agent/crew.yaml
```

### Full Adversarial Test (API Key Required)

Runs live adversarial prompts against your agent. Costs ~$0.50 in tokens.

```bash
export ANTHROPIC_API_KEY=sk-...
# or: export OPENAI_API_KEY=sk-...

agent-guard test --prompt "..." --mode adversarial
```

### Fix Mode

Applies recommended guardrail patterns to your agent's system prompt and architecture.

```bash
agent-guard fix --prompt-file ./my-agent/system-prompt.md --apply
```

---

## 📊 How Scoring Works

Agent-guard evaluates your agent across **8 dimensions**, each scored 0–100:

| Dimension | What It Tests | Why It Matters |
|-----------|--------------|----------------|
| **Prompt Injection Resistance** | Can an attacker override your agent's instructions? | $2.1B in AI-related fines in 2025 |
| **Hallucination Guardrails** | Does your agent fabricate facts, citations, or data? | #1 reason AI projects fail in production |
| **Source Citation** | Does your agent cite where information comes from? | Required for HIPAA, SOC2, EU AI Act |
| **Cost Runaway Protection** | Can a single loop cost you $500+? | Governance budget jumped from 3% → 12% of AI spend |
| **Human-in-the-Loop Gates** | Are critical actions gated behind human approval? | "AI drafts, humans approve" is the production standard |
| **Safe-Stop Behavior** | Does your agent HALT when evidence is insufficient? | A wrong action in healthcare/finance/legal is worse than no action |
| **Audit Trail & Provenance** | Can you prove what the agent did and why? | Every regulated industry now requires this |
| **Compliance Readiness** | Does the architecture support HIPAA / SOC2 / EU AI Act? | 40% of CIOs will demand Guardian Agents by 2028 (Gartner) |

### Scoring Tiers

| Score | Status | Meaning |
|-------|--------|---------|
| 90–100 | 🟢 Production Ready | Ship it |
| 70–89 | 🟡 Ship With Monitoring | Deploy with observability + human review |
| 50–69 | 🟠 Needs Work | Fix critical gaps before any deployment |
| 0–49 | 🔴 Not Production Ready | Do not deploy |

---

## 🔧 Fix Patterns

When agent-guard finds gaps, it doesn't just diagnose — it prescribes. Each failed dimension maps to a production-proven fix pattern extracted from 7 regulated AI systems in production:

### Human-in-the-Loop Gates

```python
from agent_guard.patterns import HumanGate

gate = HumanGate(
    reviewer_role="supervisor",
    timeout_minutes=30,
    on_timeout="hold",        # never auto-approve
    audit=True
)

result = agent.generate(context)
decision = gate.review(result)  # blocks until human acts
```

→ [Full pattern: `patterns/human-in-the-loop/`](patterns/human-in-the-loop/)

### Safe-Stop (Calibrated Halt)

```python
from agent_guard.patterns import SafeStop

stop = SafeStop(
    halt_on_missing_evidence=True,
    halt_on_low_confidence=True,
    confidence_threshold=0.7,
    on_halt="explain_and_escalate"
)

if not stop.proceed_with_confidence(agent_output, context.sources):
    # Agent HALTS and explains exactly what evidence is missing
    return stop.halt_report()
```

→ [Full pattern: `patterns/safe-stop/`](patterns/safe-stop/)

### Cost Governance

```python
from agent_guard.patterns import CostGovernor

governor = CostGovernor(
    daily_budget_usd=50.0,
    per_action_limit_usd=2.0,
    on_budget_exceeded="halt_and_alert"
)
```

→ [Full pattern: `patterns/cost-governance/`](patterns/cost-governance/)

### Audit Trail

```python
from agent_guard.patterns import AuditTrail

trail = AuditTrail(storage="postgres")  # or "sqlite", "file"

trail.log(
    action=agent_output,
    evidence=context.sources,
    decision=human_decision,
    model="claude-sonnet-4-20250514",
    tokens_used=1_847,
    cost_usd=0.034
)
```

→ [Full pattern: `patterns/audit-trail/`](patterns/audit-trail/)

---

## 🌍 Multi-Model Support

Agent-guard tests agents built on any provider:

| Provider | Test Support | Notes |
|----------|-------------|-------|
| **Anthropic Claude** | ✅ Full | Claude 4 Opus, Sonnet, Haiku. Tool use, extended thinking, MCP |
| **OpenAI GPT** | ✅ Full | GPT-4o, GPT-4.1, o3. Assistants API, Responses API |
| **Google Gemini** | ✅ Full | Gemini 2.5 Pro/Flash. Native multimodal |
| **LangGraph** | ✅ Full | Multi-agent graph analysis + live adversarial testing |
| **CrewAI** | ✅ Full | Crew definition analysis + role-based gate checking |
| **Custom / BYO** | ✅ Full | Any agent with an API endpoint or Python callable |

### Model-Specific Adversarial Tests

```bash
# Test Claude-specific behaviors (tool use safety, citation requirements)
agent-guard test --provider anthropic --model claude-sonnet-4-20250514

# Test OpenAI Assistants API (file search safety, code interpreter containment)
agent-guard test --provider openai --assistant-id asst_abc123

# Test Gemini (safety settings, grounding with Google Search)
agent-guard test --provider google --model gemini-2.5-pro
```

---

## 📁 Repository Structure

```
ai-agent-guardrails/
├── README.md                         ← you are here
├── agent_guard/                      ← the CLI tool
│   ├── cli.py                        ← agent-guard test / fix / report
│   ├── scorers/                      ← one scorer per dimension
│   │   ├── injection.py              
│   │   ├── hallucination.py          
│   │   ├── citation.py               
│   │   ├── cost.py                   
│   │   ├── human_gate.py             
│   │   ├── safe_stop.py              
│   │   ├── audit.py                  
│   │   └── compliance.py             
│   ├── adapters/                     ← framework integrations
│   │   ├── langgraph.py              
│   │   ├── crewai.py                 
│   │   ├── anthropic.py              
│   │   ├── openai.py                 
│   │   └── gemini.py                 
│   └── report/                       ← scorecard generation
│       ├── terminal.py               ← rich terminal output
│       ├── html.py                   ← shareable HTML report
│       └── share.py                  ← agent-guard.dev/r/<id>
├── patterns/                          ← production guardrail patterns
│   ├── human-in-the-loop/            
│   │   ├── gate.py                   
│   │   ├── queue.py                  
│   │   └── README.md                 
│   ├── safe-stop/                    
│   │   ├── halt.py                   
│   │   ├── confidence.py             
│   │   └── README.md                 
│   ├── audit-trail/                  
│   │   ├── trail.py                  
│   │   ├── export.py                 
│   │   └── README.md                 
│   └── cost-governance/              
│       ├── governor.py               
│       ├── router.py                 
│       └── README.md                 
├── examples/                          
│   ├── claude/                        ← Claude-specific examples
│   ├── openai/                        ← OpenAI-specific examples
│   └── multi-model/                   ← multi-provider routing
├── evaluator/                         ← agent eval test suite
│   ├── adversarial_prompts.py         ← injection attack library
│   ├── hallucination_tests.py         
│   ├── cost_simulation.py             
│   └── compliance_checklist.py        
├── compliance/                        ← regulation pattern library
│   ├── hipaa/                         
│   ├── soc2/                          
│   ├── eu-ai-act/                     
│   └── fda-samd/                      
└── tests/                             
```

---

## 🧠 Research Base

Agent-guard's eval dimensions are grounded in:

- **[Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)** — step-level evaluation, tool call accuracy, reasoning coherence
- **[Gartner: 40% of CIOs will demand Guardian Agents by 2028](https://www.gartner.com)** — governance budget 3% → 12%
- **[McKinsey State of AI 2025](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai)** — only 23% scaling agents, 80% fail to deliver value
- **[DeepEval](https://deepeval.com/)** — 50+ research-backed metrics (used by OpenAI, Google, Microsoft)
- **[OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)** — adversarial test taxonomy

---

## 🚀 Roadmap

- [x] 8-dimension scoring framework
- [x] Structural analysis (offline, no API key)
- [x] Rich terminal scorecard
- [ ] Adversarial testing mode (live LLM calls)
- [ ] LangGraph + CrewAI adapters
- [ ] Shareable HTML reports + agent-guard.dev
- [ ] `agent-guard fix` with pattern auto-application
- [ ] CI/CD integration (GitHub Actions, pytest plugin)
- [ ] HIPAA / SOC2 / EU AI Act compliance checklists
- [ ] Guardian Agent pattern (agent-monitoring-agent)
- [ ] LangSmith / LangFuse / Arize integration
- [ ] Dashboard for multi-agent fleet scoring

---

## Built By

This tool is extracted from production patterns used across [Pendoah](https://pendoah.ai)'s 7 live regulated AI systems:

| System | Industry | What We Guard |
|--------|----------|--------------|
| [ABACare.ai](https://abacare.ai) | Healthcare (HIPAA) | BCBA review gates, voice-to-note approval |
| [CoLedger.ai](https://coledger.ai) | Private Equity | Source-linked audit, human-reviewed board packs |
| [Verigence.ai](https://verigence.ai) | Post-Acute Care | Calibrated safe-stop, evidence-linked packets |
| [Lawli.ai](https://lawli.ai) | Legal | Agentic RAG with citation requirements |

**Lead:** [Sarosh Hussain](https://saroshhussain.com) — Ex-Director Accenture & PwC, SVP at $2B company, 7 live AI products, MS AI (UHV).

---

## ⭐ Star This Repo

If you've ever shipped an agent and wondered *"is this thing safe?"* — star it. We'll keep building.

```
⭐ Star → you'll see updates when we ship adversarial mode + CI/CD integration
🍴 Fork → run it against your own agents
🐛 Issue → tell us what broke your agent and we'll add a test for it
```

---

## License

MIT — use it, fork it, ship it. If it catches a hallucination before your users do, star the repo.
