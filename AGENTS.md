# CrewScore — agent instructions

## What this is

Offline CLI that **structurally** scores AI agent system prompts for production-readiness signals (injection defense, hallucination policy, citations, cost limits, human gates, safe-stop, audit, compliance), applies fix patterns, and optionally runs a non-technical AI vendor checklist (self-attest only).

Public brand: **CrewScore** · Domain: **https://crewscore.ai** · PyPI: **`crewscore`** · Repo: **shmindmaster/crewscore**

It does **not** (yet) run live adversarial LLM attacks or parse LangGraph/CrewAI runtimes. For live testing, hand off to Promptfoo / garak — see `docs/next-steps-eval.md`.

## Stack

- Python 3.11+
- click + rich
- hatchling packaging
- pytest

## Commands

```bash
# install (editable)
pip install -e ".[dev]"

# repo scan (preferred for CI / monorepos)
crewscore scan .
crewscore scan . --json --threshold 50

# score a single prompt
crewscore test --prompt "You are a helpful assistant..."
crewscore test --prompt-file ./system-prompt.md --explain
crewscore test --prompt-file ./system-prompt.md --json --explain
crewscore test --prompt-file ./system-prompt.md --json --threshold 50
crewscore test --prompt-file ./system-prompt.md --report out.html --badge badge.svg

# apply guardrail patterns
crewscore fix --prompt-file ./system-prompt.md --plan          # dry-run: list planned dimensions, no write
crewscore fix --prompt-file ./system-prompt.md --dry-run       # alias for --plan
crewscore fix --prompt-file ./system-prompt.md
crewscore fix --prompt-file ./system-prompt.md --apply
crewscore fix --prompt-file ./system-prompt.md --output ./guarded.md --json

# vendor checklist (secondary / self-attest)
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json

# after pattern changes: keep web in lockstep
python scripts/export_web_engine.py

# tests
pytest
```

Legacy CLI entry point `agent-guard` still maps to the same `crewscore.cli:main` after install.

## Layout

```
crewscore/
  cli.py                 # click entry (test, fix, scan, rules, export-eval)
  scoring.py             # shared result model / tiers
  profiles.py            # artifact classification -> which ruleset applies
  smells.py              # offline config-smell detection (arXiv:2606.15828)
  rules_catalog.py       # open rule catalog + per-dimension provenance
  summary.py             # PR/job markdown (transparent)
  vendor_scorecard.py    # assess-vendor command
  web_export.py          # builds score-engine.js payload
  report.py              # HTML report + SVG badge
  scorers/
    structural_analysis.py
    fix_patterns.py
scripts/export_web_engine.py
scripts/score_corpus.py  # examples/corpus leaderboard
examples/corpus/         # synthetic bare→hardened demo fixtures
score-engine.js          # generated — commit after pattern changes
index.html               # builder-first site (uses score-engine.js)
action.yml               # composite GH Action (scan/test + sticky PR comment)
docs/demo.svg            # README hero demo graphic
docs/next-steps-eval.md  # Promptfoo / garak handoff (public user doc)
tests/
```

## Product constraints

- Prefer honest capability claims over roadmap theater.
- Structural scores are pattern matches on prompt text, not proof of runtime behavior.
- **Honesty scoring:** do not claim certification, audit, or red-team results; templates can inflate scores; under-score rather than over-claim.
- **The published formula is the whole formula.** Score is a function of rule matches only. Never add a term (length, recency, file type) that isn't in `rules_catalog.SCORING_METHOD` and the README. A 0.2.x length bonus was removed in 0.3.0 precisely because it was undocumented and rewarded Context Bloat.
- **Length is never rewarded.** Every line costs the agent context on every run. Fix templates stay terse, and `fix` reports its own context cost.
- **Never hand a governance grade to coding-agent config.** `AGENTS.md`/`CLAUDE.md`-class files are judged on configuration smells (`profiles.py`). Measured on the arXiv:2606.15828 corpus, the governance ruleset scored 100/100 real config files in the worst tier — the number is meaningless for that artifact, and publishing it is the fastest way to look broken. Any new output surface (report, badge, summary, share text, web) must branch on `governance_applicable`.
- **Smells are advisory, never scored.** Folding them into the number would silently change what `--threshold N` means in someone's CI. Changing that needs corpus evidence, not a patch release.
- **Rules declare their provenance.** New dimensions must be graded `evidence-backed` / `plausible` / `author-intuition` in `rules_catalog.DIMENSION_PROVENANCE`; evidence-backed requires a citation. Approximations of a published detector must say so in their output.
- **Console output must be cp1252-encodable.** Windows redirects stdout through the ANSI code page; a stray `→` crashed `crewscore rules`. Use ASCII in printed strings.
- Prefer `crewscore scan .` / Action `scan-path` for repo-native hygiene; demote vendor checklist in UX and docs.
- Keep the package dependency-light (no LLM SDKs required for the core path).
- Fame follows usefulness: explainable findings, fix, CI gate before launch theater.
- Breaking CLI flags are acceptable if all docs and tests update in the same change.
- Never document `pip install agent-guard` as *this* product (that PyPI name is taken by another package).

## Do not

- Reintroduce fake `--langgraph` / `--crewai` loaders or adversarial mode stubs without real implementations.
- Link to non-existent report hosts or wrong GitHub/PyPI names.
- Add empty `examples/` / `evaluator/` / `patterns/` directories without content.
- Overclaim “production safety certification” or “7 regulated systems” beyond structural scanning.
- Elevate the vendor self-attest checklist to equal primary product surface.
