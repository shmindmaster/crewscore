# Contributing to CrewScore

Thanks for helping improve an offline guardrail-coverage checker for AI agent
prompts and coding-agent config.

Before proposing a change to the rules or the scoring formula, read
[`docs/validation.md`](docs/validation.md). It records the withdrawn
1,368-prompt study and the reproducible replacement corpus of 356 public
prompts (83 production-agent and 273 general-purpose). Claims remain about
*coverage*, not *quality*; new claims about what the score proves need evidence.

## Dev setup

```bash
git clone https://github.com/shmindmaster/crewscore.git
cd crewscore
pip install -e ".[dev]"
pytest -q
```

## How scoring works

- Patterns live in `crewscore/scorers/structural_analysis.py` (`SCORER_MAP`).
- Rules are grouped into controls in `CONCEPTS`; a dimension scores on how
  many of its controls the prompt states, not how many regexes fired (see
  `score_from_concepts`). Adding a synonym for a control already covered
  therefore changes no score - that is deliberate.
- Run `crewscore rules --concepts` to see the grouping.
- Explain labels: `DIMENSION_SIGNAL_LABELS` (pattern → human label pairs).
- CLI: `crewscore test`, `fix`, `assess-vendor`.
- **Web uses the same engine:** after changing patterns, regenerate:

```bash
python scripts/export_web_engine.py
pytest tests/test_web_engine.py -q
```

Commit the updated `score-engine.js` with your pattern change.

## Adding a pattern

1. Add a regex to the right list in `structural_analysis.py`.
2. Optionally add a `(pattern, human_label)` to `DIMENSION_SIGNAL_LABELS`.
3. Add/adjust a unit test in `tests/test_structural_analysis.py` or `tests/test_explain.py`.
4. Run `python scripts/export_web_engine.py` and `pytest -q`.

## Adding a fix template

Edit `crewscore/scorers/fix_patterns.py` `FIX_TEMPLATES` for the dimension key.

## PR rules

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

Read [scoring governance](docs/scoring-governance.md) before proposing a new
rule, control, or scoring change. It defines the required provenance,
validation, browser-regeneration, and changelog work. Security-sensitive
reports follow [SECURITY.md](SECURITY.md), not public issues.

Use [GitHub Discussions](https://github.com/shmindmaster/crewscore/discussions)
for questions, adoption feedback, and open-ended ideas. Use an issue form for a
reproducible defect, a safely redacted scoring report, or a scoped feature
proposal that is ready for triage.
