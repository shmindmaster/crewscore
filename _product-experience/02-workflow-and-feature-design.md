# CrewScore — Workflow & feature design

## Outcome

Builder completes a **structural preflight** on an agent prompt: knows overall hygiene, top missing signals, optionally applies text templates with consent, and leaves with share/CI next step — without believing the product is a red-team.

## Target primary workflow

```
Entry (cold / return)
  → Stage 1 PROMPT: paste | template | URL
  → Stage 2 INSPECT: score + capability stamp + top gaps + dims
  → Stage 3 ACT: plan fix → approve → re-inspect
  → Stage 4 EXPORT: share image/text | CI snippet | improved prompt
```

### Stage details

| Stage | User intent | Happy path | Empty | Error | Recovery |
| --- | --- | --- | --- | --- | --- |
| PROMPT | Provide artifact | Template or paste | Invite "Weak demo" | — | — |
| INSPECT | Understand gaps | Score + top 3 gaps | — | Engine missing | Reload |
| ACT | Improve text | Preview sections → Apply | No weak dims → "Already covered" | — | Cancel keeps original |
| EXPORT | Take result elsewhere | Share / download / CI | — | Clipboard denied | Manual select |

## Secondary workflow

**Vendor self-attest** — linked, not staged with primary. Self-attest stamp. No equal chrome.

## Information architecture

- **Primary nav:** none (single job page)
- **Progress:** step indicator 1–4 (or Prompt / Inspect / Act / Export)
- **Results hierarchy:** (1) overall + soft verdict (2) capability stamp (3) top gaps (4) dimensions (5) all rules (6) export
- **Progressive disclosure:** full rules collapsed; formula collapsed

## Agentic / AI interaction contract

CrewScore scoring is **deterministic**, not generative. The only "agent-like" action is **fix** (mutates user content).

| Action | Autonomy | Control |
| --- | --- | --- |
| Score | Auto on request | User initiates; no network model |
| Explain findings | Auto with score | Expand/collapse; open rule_ids |
| Fix plan | Preview only | List dimensions/sections that would be appended |
| Apply fix | Explicit approval | Apply / Cancel; original retained until Apply |
| Share | User-triggered | Copy text / image; disclaimer in share string |
| URL load | User-triggered | CORS failure → paste fallback |

**Prohibited claims in UI:** certification, audit complete, red-team pass, runtime safety proven.

**Uncertainty:** Always structural-only; template_boilerplate warning when fix templates detected.

## Acceptance signals

- Time from land → first score ≤ 20s with template  
- Fix cannot change text without Apply  
- After score, user sees capability stamp without scrolling past fold on desktop  
- Vendor not equal-weight with primary CTA  
- Share text includes "not a red-team"  
