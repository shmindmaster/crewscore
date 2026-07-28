# CrewScore — Discovery

**Date:** 2026-07-28  
**Repo:** `shmindmaster/crewscore`  
**Surfaces in scope:** Public web (crewscore.ai / `index.html`), CLI, GitHub Action, docs/launch.

## Product promise

Offline **structural pre-gate** for AI agent system prompts: discover missing hygiene signals, explain with open rules, fix text templates, gate CI — never claim red-team or certification.

## Users & jobs

| Persona | Job | Success looks like |
| --- | --- | --- |
| **Agent builder** (primary) | Before merge/demo, know if system prompt lacks production hygiene | Score + top gaps + fix or CI gate in <2 min |
| **OSS / HN visitor** | Understand product in 15s without install | One click demo → memorable number → trust honesty |
| **AppSec-curious** | Prefer open rules over black-box scores | Expand full rule IDs; match CLI |
| **Buyer / ops** (secondary) | Self-attest vendor diligence | Separate, demoted checklist — not the hero |

## Domain objects

- **Prompt artifact** (text / file / URL)
- **Ruleset** (`crewscore-hygiene@x.y.z`) + **rule_id** findings
- **Score result** (8 dimensions, overall, structural tier, warnings)
- **Fix pack** (appended templates; mutates text only)
- **Scan set** (repo paths; CLI/Action)
- **Share artifact** (image / text; must not overclaim)

## Capability map (what exists)

| Surface | Status | Notes |
| --- | --- | --- |
| Public marketing / demo site | Deep reviewed | Single-page score tool; primary viral surface |
| CLI `test` / `scan` / `fix` / `rules` / `export-eval` | Deep reviewed | Strong; truth source for web |
| GitHub Action + PR sticky summary | Shallow reviewed | Functional; not browser UX |
| Vendor self-attest | Shallow reviewed | Demoted; still competes for attention if tab-equal |
| Auth / billing / admin | Not applicable | Zero-install OSS |
| Live LLM / agent runtime | Not applicable | Explicitly out of scope |

## Constraints

- Deterministic scoring (no model calls on critical path)
- Browser must stay offline-capable (local `score-engine.js`)
- Honesty > virality theater
- Keep HTML contract tests (builder-first hero, authenticity, escapeHtml, engine parity)

## Evidence sources

- Runtime: live site + Playwright primary journey
- Code: `index.html`, `score-engine.js`, CLI
- Research: `docs/research/2026-07-28-useful-product-and-virality-research.md`
