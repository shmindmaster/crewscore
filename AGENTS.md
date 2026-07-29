# CrewScore — agent instructions

## What this is

Offline CLI that classifies an agent-instruction file by name and judges it one of two ways:

- **Coding-agent config** (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, and friends — see `crewscore/profiles.py`) is scanned for **configuration smells** (Context Bloat, Init Fossilization, Lint Leakage — arXiv:2606.15828) and gets **no governance score at all**.
- **Agent system prompts** (everything else) are scanned for **coverage of 8 governance-signal dimensions** (injection defense, hallucination policy, citations, cost limits, human gates, safe-stop, audit, compliance). The number is a match count against a published pattern list, not a validated quality or maturity ranking — **read `docs/validation.md` before trusting it for anything more than "which controls are missing."** In short: at matched length, CrewScore could not show production prompts scoring higher than amateur ones (delta +0.061, 95% CI −0.05 to +0.17, p=0.36), and three of the eight dimensions (Cost, Compliance, Audit) ship with known-poor construct validity.

It also applies fix patterns (system-prompt profile only — `fix` refuses to write governance templates into coding-agent config) and optionally runs a non-technical AI vendor checklist (self-attest only).

Public brand: **CrewScore** · Domain: **https://crewscore.ai** · PyPI: **`crewscore`** · Repo: **shmindmaster/crewscore**

It does **not** (yet) run live adversarial LLM attacks or parse LangGraph/CrewAI runtimes. For live testing, hand off to Promptfoo / garak — see `docs/next-steps-eval.md`.

Ruleset id: **`crewscore-hygiene@0.1.0`** (`crewscore rules` prints it; `crewscore/scoring.py:RULESET_ID` is the source of truth — it may lag this doc by a patch release mid-work).

## Stack

- Python 3.11+
- click + rich
- hatchling packaging
- pytest

## Commands

All verified by running `py -m crewscore.cli ...` on this branch (Windows; use `py`, not `python`).

```bash
# install (editable)
pip install -e ".[dev]"

# repo scan (preferred for CI / monorepos) — classifies each file (auto), scores
# system prompts on governance, config files on smells; --threshold is a no-op
# on config and says so in `warnings`
crewscore scan .
crewscore scan . --json --threshold 50
crewscore scan . --max-smells 0             # gate coding-agent config only
crewscore scan . --profile system_prompt    # force one ruleset for every file found

# score a single prompt (same auto-classification; --profile overrides it)
crewscore test --prompt "You are a helpful assistant..."
crewscore test --prompt-file ./system-prompt.md --explain
crewscore test --prompt-file ./system-prompt.md --json --explain
crewscore test --prompt-file ./system-prompt.md --json --threshold 50
crewscore test --prompt-file AGENTS.md --max-smells 0     # config CI gate
crewscore test --prompt-file ./system-prompt.md --report out.html --badge badge.svg

# apply guardrail patterns (system-prompt profile only)
crewscore fix --prompt-file ./system-prompt.md --plan          # dry-run: list planned dimensions, no write
crewscore fix --prompt-file ./system-prompt.md --dry-run       # alias for --plan
crewscore fix --prompt-file ./system-prompt.md
crewscore fix --prompt-file ./system-prompt.md --apply
crewscore fix --prompt-file ./system-prompt.md --output ./guarded.md --json

# fix refuses on coding-agent config: exits 1, prints the reason, JSON has
# "refused": true; force it anyway with --profile system_prompt (records
# "forced_governance_write": true)
crewscore fix --prompt-file AGENTS.md --plan
crewscore fix --prompt-file AGENTS.md --profile system_prompt --plan --json

# vendor checklist (secondary / self-attest)
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json

# live-eval handoff stubs (Promptfoo config + garak notes; does not run either tool)
crewscore export-eval --prompt-file ./system-prompt.md --output-dir ./crewscore-eval

# list the open rule catalog (never a black box)
crewscore rules
crewscore rules --json
crewscore rules --dimension injection

# after pattern changes: keep web in lockstep
python scripts/export_web_engine.py

# tests
pytest
```

Legacy CLI entry point `agent-guard` still maps to the same `crewscore.cli:main` after install.

## Layout

```
crewscore/
  cli.py                 # click entry (test, fix, scan, rules, export-eval, assess-vendor)
  scoring.py              # shared result model / tiers / RULESET_ID
  profiles.py             # artifact classification (filename-only) -> which ruleset applies
  scan.py                 # repo-walk file discovery + per-file scoring for `scan`
  smells.py                # offline config-smell detection (arXiv:2606.15828)
  rules_catalog.py         # open rule catalog + per-dimension provenance
  summary.py                # PR/job markdown (transparent)
  vendor_scorecard.py       # assess-vendor command
  export_eval.py             # Promptfoo/garak handoff stub writer (export-eval command)
  metrics.py                  # privacy-safe local metrics schema (no prompt text, no network)
  web_export.py                # builds score-engine.js payload
  report.py                     # HTML report + SVG badge
  scorers/
    structural_analysis.py      # governance-dimension regex matching
    fix_patterns.py               # FIX_TEMPLATES per dimension
scripts/
  export_web_engine.py             # regenerate score-engine.js after pattern changes
  score_corpus.py                    # examples/corpus leaderboard
examples/corpus/                      # synthetic bare->hardened demo fixtures
  prompts/                              # system-prompt fixtures scored by governance dimensions
  repo-config/AGENTS.md                  # config fixture scored by smells
score-engine.js                          # generated — commit after pattern changes
index.html                                 # builder-first site (uses score-engine.js)
action.yml                                  # composite GH Action (scan/test + sticky PR comment)
docs/
  validation.md                             # what the score does/does not measure — read before touching claims
  next-steps-eval.md                          # Promptfoo / garak handoff (public user doc)
  demo.svg, hero-demo.gif, hero-demo.mp4        # README hero assets
tests/
```

## Product constraints

- Prefer honest capability claims over roadmap theater.
- Structural scores are pattern matches on prompt text, not proof of runtime behavior.
- **The number is coverage, not a quality ranking.** A low score is actionable (you likely have not written a control down); a high score only means the text is present. Do not rank prompts, teams, or vendors by it, and do not treat a threshold as a safety bar — see `docs/validation.md`.
- **Honesty scoring:** do not claim certification, audit, or red-team results; templates can inflate scores; under-score rather than over-claim.
- **The published formula is the whole formula.** Score is a function of rule matches only. Never add a term (length, recency, file type) that isn't in `rules_catalog.SCORING_METHOD` and the README. A 0.2.x length bonus was removed in 0.3.0 precisely because it was undocumented and rewarded Context Bloat.
- **Length is never rewarded.** Every line costs the agent context on every run. Fix templates stay terse, and `fix` reports its own context cost.
- **Never hand a governance grade to coding-agent config.** `AGENTS.md`/`CLAUDE.md`-class files are classified by filename only (`profiles.py:classify_path`, content is never sniffed) and judged on configuration smells instead. Measured on the arXiv:2606.15828 corpus, the governance ruleset scored 100/100 real config files in the worst tier — the number is meaningless for that artifact, and publishing it is the fastest way to look broken. Any new output surface (report, badge, summary, share text, web) must branch on `governance_applicable`. `--profile` is the only override; when a caller forces governance templates onto config via `crewscore fix --profile system_prompt`, the JSON payload must carry `forced_governance_write: true` and human output must warn.
- **Config `--json` payloads carry no governance fields.** When `governance_applicable` is `false`, `overall`, `dimensions`, `findings`, and `transparency` are **absent** from `crewscore test --json` / `crewscore scan --json` output — not zeroed, omitted. Consumers read `tier`, `smells`, `source`, `warnings`, `profile`, `ruleset` instead. Do not reintroduce those fields for config rows.
- **Smells are advisory, never scored.** Folding them into the number would silently change what `--threshold N` means in someone's CI. `--max-smells N` is the separate gate for config files; changing smells into a score needs corpus evidence, not a patch release.
- **Rules declare their provenance.** New dimensions must be graded `evidence-backed` / `plausible` / `author-intuition` in `rules_catalog.DIMENSION_PROVENANCE`; evidence-backed requires a citation. Approximations of a published detector must say so in their output. Per `docs/validation.md`, Cost, Compliance, and Audit currently have known-poor construct validity — treat proposals to strengthen or remove them as scoring work needing evidence, not a doc fix.
- **Console output must be cp1252-encodable.** Windows redirects stdout through the ANSI code page; a stray arrow character once crashed `crewscore rules`. Use ASCII in printed strings.
- Prefer `crewscore scan .` / Action `scan-path` for repo-native hygiene; demote vendor checklist in UX and docs.
- Keep the package dependency-light (no LLM SDKs required for the core path).
- Fame follows usefulness: explainable findings, fix, CI gate before launch theater.
- Breaking CLI flags are acceptable if all docs and tests update in the same change.
- Never document `pip install agent-guard` as *this* product (that PyPI name is taken by another package).
- **Read `docs/validation.md` before writing or editing any claim about what the governance score proves.** It documents a discrimination study against 1,368 real prompts; do not re-inflate the "production-readiness" framing this file used before 0.1.0 without new evidence to support it.

## Do not

- Reintroduce fake `--langgraph` / `--crewai` loaders or adversarial mode stubs without real implementations.
- Link to non-existent report hosts or wrong GitHub/PyPI names.
- Add empty `examples/` / `evaluator/` / `patterns/` directories without content.
- Overclaim "production safety certification," "production-readiness," or "7 regulated systems" beyond structural scanning and coverage — see `docs/validation.md`.
- Elevate the vendor self-attest checklist to equal primary product surface.
