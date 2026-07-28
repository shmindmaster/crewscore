# CrewScore — Market Validation & Product–Market Fit Research

**Date:** 2026-07-28  
**Brand:** CrewScore · **Domain:** https://crewscore.ai · **Repo:** shmindmaster/crewscore · **PyPI:** `crewscore`  
**Research question:** Can CrewScore become a useful product with dual fame (tech + non-tech), and where is real PMF?

This brief is evidence-led. Claims are directional market signals, not audited financials. Structural prompt scoring is **useful hygiene**, not runtime proof of safety.

---

## 1. Executive verdict

| Question | Answer |
| --- | --- |
| Is there demand? | **Yes.** Agent projects fail at high rates; risk controls and cost/value gaps are named cancellation causes. |
| Is the category empty? | **No** for full LLM eval / red-team. **Yes** for *zero-friction offline system-prompt hygiene + vendor diligence scorecard* aimed at both builders and buyers. |
| Can one product serve tech + non-tech? | **Yes, with two surfaces sharing one score language** — not one UI for everyone. |
| Will prompt scoring alone create durable PMF? | **Only if honest:** market consensus is that prompt text ≠ production safety. PMF is “first useful gate + shared language,” not “certification.” |
| Path to fame | Tech: GitHub/HN/CI. Non-tech: LinkedIn vendor score + free web tool. Fame follows **decision utility**, not hype. |

**PMF hypothesis (testable):**

> Teams will adopt CrewScore when it (1) tells them what is missing in an agent prompt in under 60 seconds, (2) improves that prompt with reviewable fixes, (3) can fail CI, and (4) gives non-engineers the same vocabulary to reject weak AI vendors — without claiming false safety guarantees.

---

## 2. Market context (why now)

### 2.1 Agentic projects are under stress

- **Gartner (Jun 2025):** >40% of agentic AI projects predicted canceled by end of 2027 due to **escalating costs, unclear business value, or inadequate risk controls** — not primarily “model not smart enough.”  
  Source: [Gartner press release](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027)
- Industry commentary (Forbes et al.) reframes failure as **governance / deployment discipline**, “agent washing,” and missing override ownership.
- Practitioner literature cites high pre-production failure (often 80%+ class claims), multi-hundred-thousand-dollar failed-project costs, and demo→production gap driven by scope, data, security, integration, cost, and governance — not demos alone.

### 2.2 Production pain is concrete and public

Recurring failure themes in 2025–2026 agent write-ups:

| Pain | Manifestation | Who feels it |
| --- | --- | --- |
| **Over-permissioned agents** | Inherited engineer creds; delete/recreate prod resources | Eng + Sec + CFO |
| **Soft “confirm before act” prompts** | Treated as suggestions, not hard gates | Eng leads after incidents |
| **Prompt injection** | OWASP #1 LLM risk; high audit hit rates; indirect injection rising | Sec / AppSec |
| **Hallucinations with tools** | Wrong actions cost money, not just embarrassment | Product + Ops |
| **Cost runaway** | Unbounded tool loops, retries, token spend unforecastable | Eng + Finance |
| **Missing audit trail** | Cannot answer “what did the agent do and why?” | Compliance / Legal |
| **Shadow AI** | Unapproved tools; sensitive data into consumer AI; managers often aware | IT / Risk / Everyone |

Shadow AI signals (directional): large shares of workers use unapproved AI; executives report high personal use; bans fail. That creates **non-tech urgency** for simple diligence tools.

### 2.3 Important market truth (anti-hype)

Multiple serious sources argue **prompt-level guardrails are necessary but not sufficient**:

- Same substrate as attacks (injection).
- Bypass under long context / multi-agent propagation.
- Runtime needs: least privilege, hard stops, observability, sandboxes, data-layer governance (EU AI Act era).

**Implication for CrewScore PMF:**  
Position as **hygiene lint + shared risk language + first CI gate**, never as “production-safe certification.” Overclaiming will destroy HN/LinkedIn credibility and block B2B trust.

---

## 3. User segments & jobs-to-be-done

### Segment A — Builders (tech fame path)

| Role | Job | Current workaround | Desired outcome |
| --- | --- | --- | --- |
| Indie / startup engineer | Ship agent without looking reckless | Copy paste prompts from blogs | Instant gap list + fix draft |
| Platform / AI eng | Prevent prompt regressions | Manual PR review of huge prompts | CI threshold on score |
| AppSec-curious eng | Quick red-flag pass before garak/promptfoo | Skip security until late | Cheap first pass offline |
| Multi-agent builder | Role prompts inconsistent | Spreadsheets of prompts | Per-agent scores (future A4Squad) |

**JTBD (tech):** “When I change a system prompt, help me see production-hygiene gaps and block merges that regress them — without spinning up an eval platform.”

### Segment B — Buyers & operators (non-tech fame path)

| Role | Job | Current workaround | Desired outcome |
| --- | --- | --- | --- |
| Founder / ops lead | Pick AI vendor under time pressure | Sales demo + gut feel | 10-question score + red flags |
| Procurement / IT | Structured AI vendor diligence | 20-page Word checklists | Fast shared artifact |
| Risk / compliance lite | Prove questions were asked | Email threads | Timestamped scorecard |
| Manager of shadow AI | Respond to “can we use X?” | Ban or ignore | Diligence path in 10 min |

**JTBD (non-tech):** “Before we put company data or customers behind this AI product, help me surface missing evidence without a security team on call.”

### Segment C — Amplifiers (fame path, not primary users)

| Channel | What they share | What they need |
| --- | --- | --- |
| Hacker News / Reddit | CLI that is honest + useful | No BS, works offline |
| LinkedIn | Vendor score + red flags | Executive-readable copy |
| X | Screenshot score | One number + CTA |
| GitHub | Stars if CI-useful | Action + README truth |

---

## 4. Pain points (prioritized)

### P0 pains CrewScore can address *today*

1. **No lightweight first check** before heavy eval stacks (DeepEval, Promptfoo, garak).  
2. **Prompt regressions** ship silently (no CI on system prompts).  
3. **Buyers lack a portable diligence artifact** — lots of PDF/checklist content, little free interactive score.  
4. **Shared language missing** between eng (“prompt”) and execs (“is this safe to buy?”).

### P1 pains we must *acknowledge* and route elsewhere

5. Runtime enforcement (tool gates, IAM, sandbox) — **not** CrewScore MVP.  
6. Live adversarial resistance — owned by garak / Promptfoo red-team.  
7. Full quality metrics (faithfulness, RAG) — DeepEval / RAGAS.  
8. Continuous vendor monitoring — GRC platforms (VerifyWise etc.).

### P2 pains that create expansion revenue later

9. Multi-agent role packs (A4Squad domain).  
10. Team / department AI risk reports → Pendoah consulting.  
11. Hosted evidence vault for regulated buyers.

---

## 5. Competitive landscape & whitespace

### 5.1 Heavy tech stack (do not compete head-on)

| Tool | Job | Cost/friction | Relation to CrewScore |
| --- | --- | --- | --- |
| **DeepEval** | Metric / pytest eval | API judges, Python-native | Downstream quality |
| **Promptfoo** | Red-team + YAML evals | Config + often LLM | Downstream security |
| **garak (NVIDIA)** | Live vuln scanning | Heavier, API targets | Downstream red-team |
| **Guardrails AI / NeMo** | Runtime validators | Integrate in app | Runtime layer |
| **Langfuse / Arize** | Observability | Always-on stack | Post-deploy |

**Whitespace:** *Offline, zero-API, 30-second system-prompt structural scorecard + one-command fix + CI exit code + non-dev vendor mode.*

No major OSS brand currently owns “eslint for agent system prompts” with a dual non-dev vendor face under one simple brand.

### 5.2 Non-tech landscape

- Flood of **AI vendor due diligence checklists** (consulting PDFs, ACC questionnaires, LinkedIn posts).  
- GRC vendors sell **vendor risk modules** (heavier, paid).  
- Gap: free, delightful, shareable **score** with red flags and copy-paste LinkedIn/post text.

### 5.3 Positioning map

```
                    Lightweight / free
                           ▲
                           │
         CrewScore ●       │      Checklist PDFs
         (target)          │
                           │
  Offline ─────────────────┼───────────────── Live/API
                           │
         Linters           │   DeepEval / Promptfoo / garak
         (few)             │
                           ▼
                    Heavy platform
```

---

## 6. Solution fit

### 6.1 What fits well (keep / strengthen)

| Capability | Fit | Why |
| --- | --- | --- |
| Structural 8-dimension scan | Strong for hygiene | Maps to known failure themes (injection language, HITL, cost, audit, compliance wording) |
| `fix` templates | Strong if reviewable | Turns score into action |
| `--json` + `--threshold` | Strong for eng PMF | Real CI utility |
| `assess-vendor` 10 Qs | Strong for non-tech PMF | Matches diligence literature themes |
| Honest limits in README | Critical | Avoids “prompt guardrail fallacy” trap |

### 6.2 What fits poorly if over-sold

| Claim | Risk |
| --- | --- |
| “Production ready” as binary truth | Experts reject; runtime literature contradicts |
| Adversarial mode as differentiator | garak already owns; half-baked hurts trust |
| PyPI `agent-guard` | Name collision — must stay `crewscore` |

### 6.3 Dual-audience product architecture (required for dual fame)

| Surface | Audience | Entry | Output | Success metric |
| --- | --- | --- | --- | --- |
| **A. Web score (crewscore.ai)** | Non-tech + tech trial | Paste prompt / vendor Qs, no install | Score, red flags, share copy | Completes / shares / return visits |
| **B. CLI `crewscore`** | Tech | `pip install crewscore` | Score, fix, JSON | Weekly CI runs, GitHub stars |
| **C. GitHub Action** | Tech teams | One YAML line | PR gate | Public workflows referencing us |
| **D. HTML report** | Both | Attach to PR / email | Portable evidence | Downloads / PR comments |

Same dimensions, different UX. Non-tech never sees terminal; tech never forced through marketing site.

### 6.4 Messaging by audience (useful, not hype)

| Audience | Promise | Anti-promise |
| --- | --- | --- |
| Tech | “Lint agent system prompts offline. Fix gaps. Fail CI on regression.” | Not a red-team suite |
| Non-tech | “Ten questions. A score. Red flags before you buy or deploy AI.” | Not a security certification |
| Shared | “A common score language for builders and buyers.” | Not proof the model will obey |

---

## 7. PMF validation plan (evidence before fame)

### Stage 0 — Product honesty gate (now)

- [x] Brand/domain: CrewScore / crewscore.ai  
- [x] Free PyPI name: `crewscore` (not taken `agent-guard`)  
- [ ] Install works globally after publish  
- [ ] Explainable findings (why each dimension scored)  
- [ ] Web path equal quality to CLI for vendor mode  

### Stage 1 — Problem interviews (N=12, 2 weeks)

**Tech (6):** “How do you review system prompts today? Last production scare?”  
**Non-tech (6):** “Last AI tool purchase — what questions did you ask? What did you skip?”

Pass criteria: ≥8/12 describe a pain CrewScore maps to without prompting the product name.

### Stage 2 — Concierge usefulness test (N=20)

- 10 engineers: run on real prompts; measure score delta after `fix` **and** whether they keep the fixed text.  
- 10 buyers: complete vendor scorecard on a real vendor under consideration; measure whether they change a decision or document a ask-list.

Pass criteria:

- Tech: ≥50% keep ≥1 fix section or add CI threshold.  
- Non-tech: ≥50% use output in a real email/Slack/LinkedIn or vendor call.

### Stage 3 — Public soft launch (fame only after Stage 2)

- Show HN / Reddit for CLI.  
- LinkedIn for vendor mode.  
- Dual CTA: “Score a prompt” vs “Score a vendor.”

### Fake door metrics to kill features early

| Feature | Kill if |
| --- | --- |
| Adversarial mode | <10% of power users enable after 30 days |
| Paid individual reports | No conversion after 1k free scores |
| 200 SEO job pages (other product) | Bounce >80% / no share |

---

## 8. Risks to PMF

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Experts mock structural scoring as theater | High | Honest README; “structural only”; link to runtime controls |
| Confused with PyPI `agent-guard` (other package) | High | Brand CrewScore only; document collision |
| Non-tech never installs CLI | High | **Web-first** for vendor path on crewscore.ai |
| Fix patterns game the score without real controls | Medium | Fix copy must say “wire runtime gates” |
| Dual brand dilution (agent-guard vs CrewScore) | Medium | Single public name: CrewScore |
| Category captured by platforms | Medium | Stay wedge: lint + diligence, integrate outward |

---

## 9. Backlog implications (usefulness-first, dual audience)

### Must ship for PMF evidence

1. Publish `crewscore` to PyPI; docs only use real install string.  
2. **Explain mode** — show matched/missing signals per dimension.  
3. **crewscore.ai** static site: agent paste + vendor questionnaire (parity with CLI).  
4. HTML report for PR/email evidence.  
5. Official GitHub Action.  
6. 12 problem interviews + 20 concierge tests logged in Linear.  

### Defer until evidence

- Live adversarial mode  
- Framework graph parsers (unless one popular path is validated)  
- Hosted multi-tenant accounts  
- Consulting funnel hard-sell  

### Fame channels mapped to product proof

| Channel | Prerequisite product proof |
| --- | --- |
| HN / GitHub | Real install + useful CLI + honest limits |
| LinkedIn | Web vendor score + red flags + copy |
| X | Screenshot of either surface |
| Pendoah pipeline | Team/vendor reports that change purchases |

---

## 10. Success metrics (PMF vs vanity)

| Metric | Vanity | PMF signal |
| --- | --- | --- |
| GitHub stars | Alone | Stars *with* Action/CI references in public repos |
| PyPI downloads | Alone | Repeat installs / CI traffic pattern |
| LinkedIn shares | Alone | Shares that include red-flag content from real vendor scores |
| Score completions | Alone | Fix apply rate; threshold in CI; decision change quotes |

**90-day PMF bar (ambitious but grounded):**

- 500+ GitHub stars **or** 5 public CI usages  
- 1k+ PyPI downloads with non-trivial repeat  
- 20 written user quotes (10 tech / 10 non-tech) that name a decision improved  
- Zero major trust incidents from overclaim  

---

## 11. Recommendation

1. **Commit to CrewScore as dual-audience product** (not CLI-only OSS vanity).  
2. **Win tech** on offline lint + CI; **win non-tech** on free vendor diligence score.  
3. **Earn fame only after Stage 2 usefulness tests.**  
4. Keep vertical portfolio domains (`abacare.ai`, etc.) separate; use **crewscore.ai** for this wedge; reserve **a4squad.com** for multi-agent expansion if Stage 2 shows multi-role demand.

---

## 12. Source index (selected)

- Gartner agentic AI cancellation forecast (risk controls / cost / value) — gartner.com newsroom 2025-06-25  
- Forbes commentary on Gartner 40% forecast — 2026  
- Production agent failure / guardrail / injection literature — Codingscape, Atlan, AGAT, TrueFoundry, MintMCP, Iternal, arXiv “prompt guardrail fallacy” class arguments  
- AI vendor due diligence checklists — InitializeAI, Captain Compliance, VerifyWise, ACC questionnaire, LinkedIn diligence posts  
- Shadow AI adoption risk — OffSec, Zylo, Journal of Accountancy / Cybernews survey signals, Wiz, Deloitte State of AI references  
- Eval stack comparisons — DeepEval alternatives, Promptfoo vs DeepEval practitioner guides  

*Refresh this brief after Stage 1–2 interview evidence; code and live user behavior outrank secondary research.*
