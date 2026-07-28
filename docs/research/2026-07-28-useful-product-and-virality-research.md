# CrewScore — Useful Product & Virality Research (hard version)

**Date:** 2026-07-28  
**Status:** Directional research for product honesty — not a launch plan  
**Question:** What do users actually need, why do some OSS tools explode, and how can scoring be authentic enough that this is *useful* rather than a gimmick questionnaire?

---

## 0. Executive answer (no theater)

| Question | Straight answer |
| --- | --- |
| Will CrewScore go viral like OpenClaw / OpenWork? | **Almost certainly not in its current form.** Those products *do work for the user*. CrewScore *judges text*. Different animal. |
| Is the pain real? | **Yes.** Agent projects fail on cost, value, and risk controls — not “model not smart enough.” |
| Is a questionnaire useful? | **Barely.** Vendor 10-Q is diligence theater unless it produces evidence people act on. Not the product. |
| Is structural scoring useful? | **Yes, as ESLint-class hygiene** — if honest, evidence-based, hard to game, and embedded where prompts live. |
| Is current scoring “authentic / proper”? | **Not yet.** It is deterministic regex coverage of prompt text. Useful smoke test; **not** safety, **not** production proof. |
| What would make a *useful* product (no company required)? | Score **real agent artifacts in repos**, explain with evidence, fail CI, refuse to overclaim, and hand off to real red-team tools. |

**North star if you want useful over famous:**

> Be the thing a builder runs *before* Promptfoo/garak — like `eslint` before a security pen test — and never pretend to be the pen test.

---

## 1. What actually went viral (measured)

Live GitHub signals (fetched 2026-07-28 via API):

| Repo | Stars (approx) | What it *is* | Why people care |
| --- | --- | --- | --- |
| **openclaw/openclaw** | **~384k** | Personal AI assistant that *acts* (messaging, tools, own devices) | Does daily work; privacy / “own your stack”; identity (“lobster way”); meme + timing + influencer amplify |
| **x1xhlol/system-prompts-and-models-of-ai-tools** | **~142k** | Dump of real product system prompts | Curiosity + craft: “what do the winners actually write?” |
| **promptfoo/promptfoo** | **~24k** | Eval + red-team for apps/agents/RAG | Serious teams need *live* tests; CI-native; used by big labs |
| **different-ai/openwork** | **~17k** | OSS alternative to Claude Cowork | Desktop + MCP sharing; *workflows people run*, not score |
| **NVIDIA/garak** | **~8.6k** | LLM vulnerability scanner | Known attacks, security teams, offline/probes |
| **hermes-labs-ai/lintlang** | **~52** | Static linter for agent configs/prompts (zero-LLM CI) | **Closest category cousin** — almost no stars |
| **shmindmaster/crewscore** | **0** | Structural prompt scorecard | Not in market yet |

### Pattern: viral OSS that became “real”

OpenClaw / OpenWork / desktop “coworker” agents share a pattern:

1. **Outcome product** — user gets work done (message, file, workflow), not a report about work.  
2. **Replaces a paid closed thing** or a painful status quo (“Claude Cowork but open,” “assistant on my machine”).  
3. **Identity + demo in 30s** — GIF, desktop window, chat thread; not a form.  
4. **Timing** — privacy scares, hype of agents, influencer/press.  
5. **Network loops** — skills, connectors, MCP, shared workflows → people invite others.

**Static prompt linters do not share that pattern.** lintlang at ~52 stars is the warning light: the category CrewScore currently sits in is **not** a natural viral category. Useful ≠ viral.

### What the system-prompts mega-repo proves

People obsess over **what good agent instructions look like**. That is demand for:

- examples of production-ish prompts  
- craft quality  
- “am I missing something obvious?”

That demand supports a **craft / hygiene tool** — not a 10-question buying form.

---

## 2. Real user pain points (who hurts, how)

### 2.1 Market-level (not Twitter vibes)

Gartner (Jun 2025): **>40% of agentic AI projects predicted canceled by end of 2027** due to:

1. Escalating **costs**  
2. Unclear **business value**  
3. Inadequate **risk controls**

Not “model dumb.” Forbes / CIO follow-ons: governance, ownership, rollback, over-permissioning wipe ROI.

### 2.2 Builder pain (primary user if you want useful)

| Pain | How it shows up | What they do today | What actually helps |
| --- | --- | --- | --- |
| **Demo → prod cliff** | Agent looks smart; deletes/emails/spends | Hope + manual review | Hard gates in *runtime* + checklist of missing gates |
| **Prompt regressions** | Someone “improves” prompt, removes HITL language | PR vibes | CI that fails on missing signals / score drop |
| **Too much tool surface** | Agent inherits engineer creds | Panic after incident | Least-privilege tooling (outside CrewScore) |
| **Eval stack friction** | Promptfoo/garak need config, keys, time | Skip until late | **Zero-setup first pass** |
| **Prompt craft FOMO** | “Is my system prompt trash?” | Copy Twitter prompts | Evidence: what’s missing vs public norms |
| **Multi-file agent config** | prompts in YAML, LangGraph, OpenClaw, Cursor rules | Grep by hand | **Repo scan** finding those files |

**JTBD (builder):**  
*When I change agent instructions, show me production-hygiene gaps with evidence in under a minute, and fail the build if we regressed — without standing up an eval platform.*

### 2.3 Security / platform pain

| Pain | Tool they trust | CrewScore’s lane |
| --- | --- | --- |
| Live jailbreak / injection resistance | garak, Promptfoo red-team | **Not us** — link out |
| App-specific multi-turn agent attacks | Promptfoo agents suite | **Not us** |
| First cheap filter before expensive runs | Often nothing | **Possible us** |

### 2.4 Buyer / non-tech pain (secondary)

| Pain | Reality check |
| --- | --- |
| Vendor vapor demos | Real — but they use **sales security questionnaires**, SOC2 PDFs, legal — not a free web quiz |
| Shared language with eng | Soft value |
| 10-question self-attest score | Easy to game; low trust as “product” |

**Conclusion:** Dual-audience is a *marketing* idea. A *useful* product optimizes for **builders first**. Vendor mode is optional spice, not the core.

---

## 3. Competitive truth (do not lie to yourself)

| Layer | Owners | Friction | Stars order |
| --- | --- | --- | --- |
| **Do the work (agents)** | OpenClaw, OpenWork, Coworker clones | Install / desktop / model | 10k–100k+ |
| **Live eval / red-team** | Promptfoo, garak, PyRIT, DeepEval | Config + often LLM cost | ~5k–25k |
| **Runtime guardrails** | Guardrails AI, NeMo Guardrails, app IAM | Integration | product-dependent |
| **Static prompt/config lint** | lintlang, PromptLint-class, aiproof-class, **CrewScore** | Low | **tens to low hundreds unless distribution hits** |
| **Prompt pornography / education** | system-prompts dumps | Zero | **100k+** |

**Whitespace that is real but small:**

> Offline, zero-API, evidence-backed structural hygiene on *agent instruction artifacts*, CI-native, aggressively honest about limits.

**Whitespace that is fake:**

> “Production readiness score that means the agent is safe.”

---

## 4. Authenticity of scoring — current CrewScore vs “proper”

### 4.1 What CrewScore does today (truth)

- Offline regex / pattern match on **system prompt text**  
- 8 dimensions, equal weight → 0–100 + tier labels  
- `fix` appends templates → score often jumps ~0 → ~46 without any runtime change  
- Browser and CLI share exported patterns  
- Vendor mode: **self-attested answers** → arithmetic score  

### 4.2 Authenticity failures (call them out)

| Failure | Why it breaks trust |
| --- | --- |
| **Keyword theater** | Matching `safety\|guardrail` can inflate scores without real policy |
| **Fix = score gaming** | Paste boilerplate → higher number without tool gates, budgets, logging |
| **Equal weights** | Compliance keywords ≠ same as human approval before wire transfer |
| **No corpus validation** | Patterns not measured against real incident prompts / open agent repos |
| **Tier language** | “PRODUCTION READY (structurally)” still reads as certification to skim readers |
| **Vendor self-score** | Answering “yes” to everything yields TRUSTED — pure honor system |
| **Not runtime** | Market consensus: prompt text ≠ model obedience |

### 4.3 What “proper / authentic scoring” would require

Minimum bar for something people don’t laugh at on HN:

1. **Evidence, not vibes** — every point cites matched snippet or explicit missing rule ID.  
2. **Deterministic + versioned rule pack** — `ruleset: crewscore-hygiene@0.2.1`, changelog when rules change.  
3. **Hard to game** — fixing should require *specific* policy content; penalize generic “be safe”; optional “template detected” warning.  
4. **Separate scores** — never mix:  
   - `hygiene_text` (structural)  
   - `self_attest_vendor` (checklist)  
   - never a single “safety score”  
5. **False-positive honesty** — document known weak patterns; invite FPs as GitHub issues.  
6. **Ground in public norms** — score against patterns mined from real open agent prompts (with license respect), not only author intuition.  
7. **Explicit non-scores** — print: “This does not measure jailbreak resistance. Use garak/Promptfoo.”  
8. **Optional deeper modes later** — only after hygiene earns trust: optional LLM-judge or live probe *as separate product surface*, never blended into the free offline number.

### 4.4 What “easy” means for users (from viral tools)

OpenClaw / OpenWork win on **path of least resistance to value**:

| Easy | Not easy |
| --- | --- |
| One install, one obvious action | Multi-tab questionnaire first |
| Works on *their* artifacts (desktop, MCP, chat) | Paste abstract prompt only |
| Demo GIF / one command | “Read 8 dimensions” |
| Shares something cool | Shares a homework form |

For CrewScore “easy” should mean:

```bash
# dream path (useful product)
crewscore scan .                 # finds agent prompts/configs in repo
crewscore scan . --threshold 50  # CI
crewscore explain path/to/prompt.md
```

Not: land on site → vendor tab → 10 buttons.

---

## 5. Why OpenClaw / OpenWork went from viral to “company-shaped” (and what that means for you)

You said: **don’t want a company; want useful.**

What those projects did after attention:

- **OpenClaw:** foundation / ecosystem / connectors / enterprise variants appear around the core *assistant that runs*.  
- **OpenWork:** desktop + MCP + org “Den” control plane — still centered on *running shared capabilities*.

They did **not** start as scorecards. They started as **tools people run every day**.

Implication for you:

| If you want… | Then… |
| --- | --- |
| Viral mega-hit | Build something people *run* (agent, skill pack, OpenClaw plugin) — not a linter score |
| Useful tool people keep | Own a **sharp hygiene job** in the agent lifecycle and stay boring/honest |
| Both | Unlikely; pick useful first, accept small distribution |

**Useful without company:**

- Single maintainer OSS is fine  
- PyPI + GH Action + clear ruleset  
- No SaaS required  
- Success metric: **weekly active CLI runs / CI installs / issues about false positives** — not star theater

---

## 6. Revised product thesis (useful, not questionnaire)

### Kill / demote

- Vendor questionnaire as hero  
- “Production ready” as headline language  
- Implied equivalence between fix templates and real safety  

### Keep / sharpen

- Offline structural scan with **evidence**  
- CI threshold  
- Explain mode  
- Brutal honesty  

### Build next (usefulness order)

| Priority | Capability | Why |
| --- | --- | --- |
| P0 | **Repo scan** (`crewscore scan .`) for `AGENTS.md`, system prompts, common agent YAML | Meets builders where work lives |
| P0 | **Rule IDs + evidence snippets** in every finding | Authenticity |
| P0 | **“Template detected” / gaming warning** when fix boilerplate dominates | Trust |
| P1 | **PR comment Action** (score delta on PR) | Distribution inside real workflows |
| P1 | **Export pack for Promptfoo/garak** (“next steps” config stub) | Honest pipeline, not competition |
| P1 | **Public corpus tests** — score known open agent prompts; publish expected ranges | Credibility |
| P2 | Optional live adversarial *separate command* | Only after hygiene trust |
| P3 | Vendor mode kept as `assess-vendor`, never homepage hero | Secondary |

### Success metrics that mean “useful” (not vanity)

1. Someone adds Action to a real agent repo unprompted  
2. False-positive issues filed (people care enough to argue rules)  
3. Score delta used in PR discussion  
4. Installs after Show HN without you spamming  
5. Zero angry “this claims safety” threads — or you fix copy until gone  

If after soft launch **none** of 1–4 happen: thesis failed; keep as personal utility or sunset theater.

---

## 7. Honest scoring charter (proposal to ship in README)

Copy-ready principles:

1. CrewScore measures **presence of hygiene signals in text**, not agent behavior.  
2. Scores are **rule-pack versioned** and deterministic for a given pack.  
3. Every finding must show **match evidence or explicit missing rule**.  
4. `fix` improves **text coverage**, not runtime safety; output always says so.  
5. We never call a score a **certification**, **audit**, or **red-team result**.  
6. When in doubt, **under-score** rather than inflate.  
7. Rules change only with changelog; CI consumers can pin pack versions later.

---

## 8. Comparison: viral product DNA vs CrewScore DNA

| DNA | OpenClaw / OpenWork | CrewScore today | CrewScore if useful |
| --- | --- | --- | --- |
| Core loop | Do task | Rate pasted text | Rate **repo agent artifacts** |
| Emotional hit | Power / ownership | Mild shame/score | “Caught a real gap before merge” |
| Moat | Ecosystem, connectors | None | Rule quality + trust + CI habits |
| Virality path | Demo of agent working | Screenshot of number | PR comment + HN honesty |
| Failure mode | Ops complexity | Seen as quiz / regex | Stays niche but respected |

---

## 9. Recommendations (do not take lightly)

1. **Stop selling virality.** Sell usefulness. Measure CI and FPs.  
2. **Demote vendor questionnaire** in product and marketing.  
3. **Invest authenticity before announce spam:** rule IDs, evidence, anti-gaming, versioned pack.  
4. **Build `scan .` next** — biggest jump from “toy form” to “dev tool.”  
5. **Position explicitly under Promptfoo/garak** as pre-gate, not peer.  
6. **Use system-prompt culture:** score famous public prompts as examples of craft gaps (educational), with licenses respected.  
7. **If you still want viral energy:** ship an **OpenClaw / OpenWork skill or plugin** that runs CrewScore on the agent’s own instruction file — ride *their* loops instead of inventing a scorecard company.

---

## 10. Sources (primary / secondary)

- Gartner press release, 2025-06-25: agentic project cancellation drivers (cost, value, risk controls)  
- Forbes / CIO commentary on governance and over-permission (2026)  
- GitHub API star counts: openclaw, openwork, promptfoo, garak, lintlang, system-prompts repo, crewscore (2026-07-28)  
- Promptfoo docs/blog: agent red-team, comparison with garak  
- lintlang README: zero-LLM static gating category  
- OpenWork README: OSS Claude Cowork alternative, MCP sharing  
- OpenClaw secondary analyses: self-hosted agent runtime, privacy timing, influencer amplification  
- Prior internal brief: `docs/pmf-research-2026-07-28.md` (partially optimistic; this doc overrides dual-audience primacy)

---

## 11. Bottom line

**Pain is real.**  
**Your current packaging can look like a questionnaire anyone can build** — because the vendor surface *is* that, and the agent surface is still “paste text, get regex score.”  
**Viral mega-agents sell power.** You are not that product.  
**A useful product is still available:** ruthless honesty + repo-native hygiene + evidence-backed rules + CI — the boring tool people keep after the lobster memes die.

If you only do one thing after this research: **make scoring harder to mock and easier to run on a real agent repo.** Everything else is noise.
