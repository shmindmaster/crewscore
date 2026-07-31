# Contributing to CrewScore

Thanks for helping improve an offline guardrail-coverage checker for AI agent
prompts and coding-agent config.

CrewScore is created and maintained by **Sarosh Hussain**. **Pendoah** is the
company operating context for the project; technical claims should be checked
against the code, tests, and cited validation material.

Before proposing a change to the rules or the scoring formula, read
[`docs/validation.md`](docs/validation.md). It records the withdrawn
1,368-prompt study and the reproducible replacement corpus of 356 public
prompts (83 production-agent and 273 general-purpose). Claims remain about
*coverage*, not *quality*; new claims about what the score proves need evidence.

## Dev setup

Full local workflow, packaging, and media policy:
**[docs/development.md](docs/development.md)**.

```bash
git clone https://github.com/shmindmaster/crewscore.git
cd crewscore
pip install -e ".[dev]"
pytest -q
```

## How scoring works

See **[docs/scoring-and-controls.md](docs/scoring-and-controls.md)**. Short version:

- Patterns live in `crewscore/scorers/structural_analysis.py` (`SCORER_MAP`).
- Rules are grouped into controls in `CONCEPTS`; a dimension scores on how
  many of its controls the prompt states, not how many regexes fired.
- CLI: `crewscore test`, `scan`, `fix`, `rules`, `baseline`, `init`, plus
  secondary `export-eval` and `assess-vendor`.
- **Web uses the same engine:** after changing patterns, regenerate
  `score-engine.js` with `python scripts/export_web_engine.py`.

## PR rules

- **How review works here:** merges are gated by CI status checks (pytest,
  browser suite, self-test, web-engine drift), not by a required human
  review. Maintainer PRs auto-merge when checks pass. External PRs are still
  read by a maintainer before merge — the automation replaces the process
  gate, not the attention. Don't wait on a review request to iterate; green
  checks are the signal that matters.
- Prefer TDD for behavior changes.
- Keep claims honest: structural ≠ runtime red-team.
- Never document `pip install agent-guard` as this product.
- Do not add LLM API dependencies for the core path.

## Code of conduct

The full [Code of Conduct](CODE_OF_CONDUCT.md) applies to every project space.
For scoring reports, use the false-positive or false-negative issue forms and
provide a minimal synthetic or safely redacted example - never customer prompt
text, credentials, or private source URLs.

## Governance and community

Read [scoring governance](docs/scoring-and-controls.md#scoring-governance-how-rules-change)
before proposing a new rule, control, or scoring change. It defines the
required provenance, validation, browser-regeneration, and changelog work.
Security-sensitive reports follow [SECURITY.md](SECURITY.md), not public issues.

Use [GitHub Discussions](https://github.com/shmindmaster/crewscore/discussions)
for questions, adoption feedback, and open-ended ideas. Use an issue form for a
reproducible defect, a safely redacted scoring report, or a scoped feature
proposal that is ready for triage.
