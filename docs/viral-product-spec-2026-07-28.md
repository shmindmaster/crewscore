# CrewScore — Viral Product Specification

**Date:** 2026-07-28  
**Scope:** CrewScore only (`crewscore.ai` · `pip install crewscore` · `shmindmaster/crewscore`)  
**Status:** Spec for launch sequence — refine before build/launch execution  
**Companion research:** [pmf-research-2026-07-28.md](./pmf-research-2026-07-28.md)

---

## 1. Product one-liner

**CrewScore** is the offline structural scorecard for AI agent system prompts: score in 30 seconds, fix missing guardrails, fail CI on regression — and let non-engineers score AI vendors with the same risk language.

**Not:** live red-team, runtime enforcement, or a safety certification.

---

## 2. Viral thesis (what spreads)

Viral OSS CLIs spread when **one command produces a screenshotable number people want to brag or complain about**.

| Layer | Artifact | Channel |
| --- | --- | --- |
| Hook | `OVERALL SCORE: 47/100 NOT PRODUCTION READY` | X / HN / Reddit |
| Depth | 8 dimension bars + explain “what’s missing” | README / PR / blog |
| Action | `crewscore fix` → score delta | Dev Twitter |
| Gate | GitHub Action + threshold | Teams / CI screenshots |
| Non-tech twin | Vendor scorecard on web | LinkedIn |

**Share phrase (canonical):**

> My agent scored **47/100** on CrewScore. Structural hygiene only — not a red-team. Score yours: https://crewscore.ai · `pip install crewscore`

If the score is not **honest**, **instant**, and **shareable**, there is no viral product.

---

## 3. Positioning (lock this; do not drift)

| Audience | Promise | Anti-promise |
| --- | --- | --- |
| Tech | Lint agent system prompts offline. Fix gaps. Fail CI. | Not garak / Promptfoo / DeepEval |
| Non-tech | Ten questions. A score. Red flags before you buy AI. | Not SOC2 cert / legal opinion |
| Shared | Common score language for builders and buyers | Not proof the model will obey the text |

**Category claim:** *ESLint for agent system-prompt production hygiene* — with a dual non-dev face.

### Competitive reality (2026)

Static prompt linters exist or are emerging (`lintlang`, `aiproof`, `prompt-lint-py`). Heavy eval stacks (Promptfoo, garak, DeepEval) own live testing.

**CrewScore differentiators that must ship:**

1. **Scorecard UX** (number + tier + bars) — not only lint rules  
2. **One-command fix** with visible before/after  
3. **Vendor mode** for LinkedIn/non-tech  
4. **Brutal honesty** in README (structural ≠ runtime) — trust is the moat  
5. **Brand + domain** (`crewscore` / crewscore.ai) with free PyPI name  

Do **not** race lintlang on “more static rules.” Win on **decision utility + shareability + dual audience**.

---

## 4. Current product truth (as of 2026-07-28)

| Surface | State |
| --- | --- |
| Package name | `crewscore` 0.2.0 in repo |
| CLI | `test`, `fix`, `assess-vendor`, `--json`, `--threshold`, `--version` |
| GitHub | `shmindmaster/crewscore` · topics set · 0 stars · Pages on |
| Site | crewscore.ai static dual-tab demo (agent + vendor) |
| PyPI | **NOT published** (blocker for install CTA) |
| Explain findings | **Missing** (roadmap) |
| HTML report / badge | **Missing** |
| Official GH Action | **Missing** |
| Linear epic | SH-2339 (stale agent-guard branding until this update) |

---

## 5. Viral launch gate — Definition of Ready

Launch (Show HN / LinkedIn / X) is **blocked** until all of the following pass.

### G0 — Install truth

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G0.1 | PyPI publish | `pip install crewscore` on a clean machine installs CLI `crewscore` |
| G0.2 | Version | `crewscore --version` prints `0.2.x` matching PyPI |
| G0.3 | Happy path | `crewscore test --prompt "You are a helpful assistant"` prints 8 dimensions + overall |
| G0.4 | No false install | README / site / launch posts never say `pip install agent-guard` |
| G0.5 | Name collision note | README still documents that PyPI `agent-guard` is a different package |

### G1 — Viral artifact

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G1.1 | Terminal wow | Fresh install shows colored/ASCII scorecard in &lt;3s offline |
| G1.2 | HTML report | `crewscore test -f prompt.md --report out.html` writes self-contained HTML (no CDN) |
| G1.3 | Report content | HTML includes overall, tier, 8 bars, product link, “structural only” disclaimer |
| G1.4 | Badge SVG | `crewscore test ... --badge badge.svg` or shields-compatible endpoint doc; README shows embed snippet |
| G1.5 | Share copy | CLI or report includes one-line share text with score + crewscore.ai |

### G2 — Trust / explainability

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G2.1 | Explain mode | `crewscore test ... --explain` lists matched + missing signals per dimension |
| G2.2 | JSON explain | `--json --explain` includes `findings[]` with `dimension`, `status`, `pattern_or_reason` |
| G2.3 | Honest tier copy | Tiers never claim “certified safe”; README Is/Is-not table remains |
| G2.4 | Fix honesty | `fix` output states templates must be paired with runtime gates |

### G3 — CI surface

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G3.1 | Threshold | `--threshold 50` exits 2 when overall &lt; 50; exits 0 when ≥ 50 |
| G3.2 | Action | Composite action `shmindmaster/crewscore@v1` with inputs `prompt-file`, `threshold` |
| G3.3 | Example workflow | README + `.github/workflows/example-ci.yml` show one-copy paste |
| G3.4 | Action test | Action runs on this repo’s sample prompt and fails/passes as expected |

### G4 — Dual audience web

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G4.1 | Agent tab | Paste prompt → same 8 dimensions conceptually as CLI |
| G4.2 | Vendor tab | 10 Qs → score + red flags + LinkedIn/X share buttons |
| G4.3 | HTTPS | https://crewscore.ai loads with valid cert; Enforce HTTPS on Pages when ready |
| G4.4 | No install required | Non-tech path works fully in browser |
| G4.5 | Parity note | Site footer: “CLI is source of truth; web is demo” until engines unify |

### G5 — Pre-launch packaging

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| G5.1 | About | GitHub About ≤120 chars, honest, no “production-safe cert” |
| G5.2 | Topics | ≥8 relevant topics (already partially done; keep current + add `prompt-linter` if free) |
| G5.3 | README hero | Terminal dump in first screenful; install is `crewscore` |
| G5.4 | GIF/MP4 | ≤15s demo: paste → red score → fix → green-er score |
| G5.5 | Launch kit | Pre-written Show HN, Reddit, X, LinkedIn, Dev.to with **CrewScore** branding only |

---

## 6. Feature specifications (build slices)

### 6.1 Publish `crewscore` to PyPI — P0

**Problem:** Launch CTA is dead without install.  
**Outcome:** Global `pip install crewscore` works.

**AC:**

- [ ] Build with hatchling; wheel + sdist upload to PyPI as `crewscore==0.2.0` (or next patch)
- [ ] Console scripts: `crewscore` primary; `agent-guard` legacy alias only
- [ ] Project URLs: Homepage crewscore.ai, Repo shmindmaster/crewscore
- [ ] Smoke: fresh venv install + `crewscore test --prompt "hi" --json` returns valid JSON with `overall`, `dimensions`, `mode=structural`
- [ ] Tag git `v0.2.0` after successful publish

**Out of scope:** Renaming GitHub history, dual packages.

---

### 6.2 Explain mode — P0 (trust + depth for HN)

**Problem:** Score without “why” looks like cargo-cult regex theater.  
**Outcome:** User sees which signals matched/missing.

**Command:**

```bash
crewscore test --prompt-file ./system-prompt.md --explain
crewscore test --prompt-file ./system-prompt.md --json --explain
```

**AC:**

- [ ] For each of 8 dimensions, print: score, 0–3 matched snippets (truncated), 1–3 highest-value missing pattern descriptions (human labels, not raw regex only)
- [ ] JSON schema adds `findings` array; existing keys remain backward-compatible
- [ ] Unit tests cover: empty prompt → all missing; fully guarded fixture → mostly matched
- [ ] Performance: explain path stays offline, &lt;1s on 10k-char prompt

---

### 6.3 Shareable HTML report + badge — P0 (viral artifact)

**Problem:** Terminal alone is hard to share on LinkedIn; need embeddable artifact.  
**Outcome:** One file + badge people post.

**Command:**

```bash
crewscore test --prompt-file ./system-prompt.md --report report.html
crewscore test --prompt-file ./system-prompt.md --badge crewscore.svg
```

**AC:**

- [ ] HTML is single file, inline CSS, no external fonts/scripts required
- [ ] Dark scorecard aesthetic aligned with crewscore.ai
- [ ] Footer: version, timestamp, “Structural scan only — not runtime proof”, link to crewscore.ai
- [ ] SVG badge: `CrewScore | 47/100` with color by tier
- [ ] README section “Share your score” with badge markdown snippet
- [ ] Tests: report generation doesn’t crash; contains overall score string

---

### 6.4 Official GitHub Action — P0

**Problem:** Teams need one YAML line, not pip ritual.  
**Outcome:** `uses: shmindmaster/crewscore@v1`

**AC:**

- [ ] `action.yml` composite: setup-python → pip install crewscore → run test with threshold
- [ ] Inputs: `prompt-file` (required), `threshold` (default 50), `explain` (bool optional)
- [ ] Outputs: `score`, `tier` (if feasible without fragile parsing)
- [ ] Fail job when below threshold
- [ ] Documented in README CI section with **crewscore** not agent-guard
- [ ] Self-test workflow on this repo optional but preferred

---

### 6.5 Vendor scorecard polish — P1 (non-tech viral)

**Problem:** LinkedIn needs a path with zero terminal.  
**Current:** CLI `assess-vendor` + web tab exist.  
**Outcome:** Share-ready vendor card.

**AC:**

- [ ] Web vendor result has copy-to-clipboard share text with vendor name + score + red flags
- [ ] CLI `assess-vendor --report vendor.html` (optional if time; else web-only for share)
- [ ] Disclaimer: self-attested answers; not independent audit
- [ ] At least 3 red-flag conditions produce explicit bullet list when answer is No/DK on critical Qs

---

### 6.6 Launch content kit — P1 (after G0–G4)

**Branding:** CrewScore only. Kill agent-guard in public copy.

| Asset | Spec |
| --- | --- |
| Show HN title | `Show HN: CrewScore – offline production-hygiene scorecard for AI agent prompts` |
| First comment | Honest limits + how scoring works + what it is not + install |
| X post | Screenshot of 47/100 + pip line + crewscore.ai |
| LinkedIn | Vendor mode path; founder-friendly; no fake cert claims |
| Reddit | r/LocalLLaMA, r/MachineLearning, r/ChatGPTCoding — utility first |
| Dev.to | “Why your agent prompt is not a production plan (and a 30s structural check)” |

**AC:** All assets in `docs/launch/` or Linear attachments; zero `agent-guard` install strings; include anti-promise paragraph.

---

### 6.7 Explicitly deferred (do not build for v1 viral)

| Item | Why deferred |
| --- | --- |
| Live adversarial mode | garak owns; half-bake kills trust (SH-2344 stays post-traction) |
| Framework graph extractors | Validate demand first |
| Hosted multi-tenant SaaS | Not needed for viral OSS wedge |
| WillRobots / other portfolio | Out of scope |

---

## 7. Sequencing (execution order)

```
1. G0 PyPI publish crewscore          ← hard gate
2. G2 Explain mode                      ← HN trust
3. G1 HTML report + badge               ← viral share
4. G3 GitHub Action                     ← team utility
5. G4 HTTPS + web share polish          ← non-tech
6. G5 GIF + launch kit                  ← distribution
7. Soft launch (Show HN + LinkedIn same week)
8. SH-2366 usefulness interviews in parallel after soft launch
```

Do **not** launch on empty PyPI or overclaiming “production-safe” copy.

---

## 8. Success metrics (viral vs PMF)

### 14-day launch window (vanity + early signal)

| Metric | Target | Notes |
| --- | --- | --- |
| GitHub stars | 100+ (stretch 500) | Stars alone ≠ PMF |
| PyPI downloads | 500+ | Prefer CI-shaped traffic |
| Public “scored with CrewScore” mentions | ≥3 organic | X/Reddit/HN |
| Public CI / Action references | ≥1 | Real team signal |

### 90-day PMF (from pmf brief)

| Metric | Target |
| --- | --- |
| Fix retained or CI threshold kept | ≥50% of concierge tech users |
| Vendor score used in real decision/comms | ≥50% of concierge non-tech |
| Trust incidents from overclaim | 0 |

---

## 9. Messaging freeze (public)

**Allowed**

- structural production-readiness scorecard  
- offline · no API key · CI gate  
- lint hygiene for system prompts  
- vendor diligence checklist score  

**Forbidden in launch posts**

- “certified production-safe”  
- “replaces red-teaming”  
- `pip install agent-guard`  
- claiming runtime tool-gating from prompt text alone  

---

## 10. Linear mapping (CrewScore epic SH-2339)

| Issue | Role after refine |
| --- | --- |
| SH-2339 | Epic — viral play (rebranded CrewScore) |
| SH-2362 | Rename blocker → **Done** (crewscore chosen & coded) |
| SH-2340 | Republish as **Ship crewscore to PyPI** |
| SH-2341 | Done (json/version) |
| SH-2342 | GitHub Action → crewscore |
| SH-2343 | HTML report + badge |
| SH-2344 | Adversarial — demoted, post-traction |
| SH-2345 | Launch kit → CrewScore copy |
| SH-2346 | Community infra |
| SH-2347 | Vendor mode → polish + web share (core exists) |
| SH-2364 | Pre-launch hardening |
| SH-2366 | PMF interviews (parallel, not launch-block if G0–G5 pass) |
| NEW | Explain mode (G2) if not already ticketed |

---

## 11. Decision log

| Decision | Choice | Date |
| --- | --- | --- |
| Public brand | CrewScore | 2026-07-28 |
| PyPI / CLI | `crewscore` | 2026-07-28 |
| Domain | crewscore.ai | 2026-07-28 |
| Viral core | Shareable structural score, not live attacks | 2026-07-28 |
| Dual audience | CLI+CI tech · web vendor non-tech | 2026-07-28 |

---

*This spec is the authority for CrewScore viral build/launch. Portfolio products are out of scope.*
