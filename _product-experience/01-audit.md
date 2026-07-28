# CrewScore — Product experience audit

**Date:** 2026-07-28  
**Method:** Discovery + live journey (Playwright) + implementation review  
**Scope:** Public web primary; CLI/Action as continuity targets

## Coverage ledger

| Surface | Status | Notes |
| --- | --- | --- |
| Public marketing / zero-install demo | Deep reviewed | Core product surface for cold traffic |
| Customer product (web score/fix) | Deep reviewed | Same page as marketing |
| Developer integrations (CLI/Action) | Shallow reviewed | Strong utility; linked in footer |
| Vendor diligence | Shallow reviewed | Secondary; over-weighted in IA if equal tab |
| Auth / billing / ops / support portals | Not applicable | |

## Primary journey audited

**Try template → score → understand → fix → share**

Evidence (2026-07-28): Weak demo → 0/100 → Fix → 46/100 works. Full rule dump previously overloaded; polish reduced dump but **workflow still single-panel form**, not a task lifecycle.

## Findings

### F1 — Workflow is a form, not a preflight job  
**Severity:** High · **Class:** product-fix-required  
**Evidence:** One panel with score, fix, URL, vendor tab; no explicit stages, plan-before-mutate, or completion.  
**Impact:** Builders don't feel "I completed a gate"; visitors don't learn the product story.  
**Recommendation:** Stage the job: Prompt → Inspect → Act → Export.  
**Validate:** Task completion without reading docs; time-to-first-insight < 20s.

### F2 — "Fix" mutates without plan preview (agentic control gap)  
**Severity:** High · **Class:** product-fix-required  
**Evidence:** `fixAndRescore` replaces textarea immediately; no preview of sections that will be appended.  
**Impact:** Surprising text mutation; reduces trust for production prompts.  
**Recommendation:** Preview plan (dimensions/sections to add) → explicit Apply.  
**Validate:** User can cancel fix; prompt unchanged until Apply.

### F3 — Capability boundary is easy to misread as "AI safety product"  
**Severity:** High · **Class:** product-fix-required  
**Evidence:** Hero about agent prompts; scoring is regex. Honesty present but competes with marketing.  
**Impact:** Trust collapse on HN; wrong mental model.  
**Recommendation:** Persistent capability chip + result stamp: "Structural pre-gate · not red-team".  
**Validate:** After first score, user can restate what product is/isn't.

### F4 — Results still present as dashboard, not decisions  
**Severity:** Medium · **Class:** product-fix-required  
**Evidence:** 8 bars + optional full rules; top gaps improved but no "next action" hierarchy beyond Fix.  
**Impact:** Cognitive load; weak link to CI/export-eval.  
**Recommendation:** Decision stack: Top gaps (act) → dimension radar/checklist → optional rules → CI/export CTA.  
**Validate:** First click after score is gap-relevant action ≥70% of sessions (instrument).

### F5 — Vendor path steals IA equality  
**Severity:** Medium · **Class:** product-fix-required  
**Evidence:** Tab strip co-primary with agent scoring. Research demoted vendor.  
**Impact:** Dilutes builder product; resurrects questionnaire theater.  
**Recommendation:** Vendor as secondary link / `#vendor`, not equal tab chrome.  
**Validate:** Cold open shows only agent job.

### F6 — Visual system still "AI product default"  
**Severity:** Medium · **Class:** product-fix-required  
**Evidence:** Dark slate + cyan gradient + system sans; generic after 2026 AI sites.  
**Impact:** Low memorability; fails distinctive frontend-design bar.  
**Recommendation:** Preflight/instrument aesthetic — amber caution + terminal mono + radar/checklist signature.  
**Validate:** Screenshot recognition without logo text in informal test.

### F7 — Empty / error / success states underdesigned  
**Severity:** Medium · **Class:** product-fix-required  
**Evidence:** Empty = blank textarea; error = red line; success = scorecard only.  
**Impact:** No guided first action; recovery is weak for URL/CORS failures.  
**Recommendation:** Empty invites one demo; errors name cause + paste fallback; success has completion checklist.  
**Validate:** Empty state has single recommended action; URL error offers paste.

### F8 — No outcome instrumentation  
**Severity:** Medium · **Class:** product-fix-required  
**Evidence:** No events for score/fix/share (by design privacy-first, but no measurement plan either).  
**Impact:** Cannot learn if UX works post-launch.  
**Recommendation:** Privacy-safe local counters + optional anonymous funnel (no prompt text). See `06-outcome-measurement-plan.md`.

### F9 — CLI/Action continuity weak on web  
**Severity:** Low · **Class:** informational  
**Evidence:** Footer codes only.  
**Impact:** Web users don't graduate to CI.  
**Recommendation:** After score, "Gate this in CI" copy-paste block with scan/action snippet.

## Prioritized decision list

1. Redesign primary workflow stages + fix plan/apply (F1, F2)  
2. Capability stamp + decision-first results (F3, F4)  
3. Demote vendor IA (F5)  
4. Distinctive preflight visual system (F6)  
5. Empty/error/success states (F7)  
6. Measurement without prompt capture (F8)  
7. CI handoff CTA (F9)
