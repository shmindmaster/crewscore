# Contributing to CrewScore

Thanks for helping improve an offline guardrail-coverage checker for AI agent
prompts and coding-agent config.

Before proposing a change to the rules or the scoring formula, read
[`docs/validation.md`](docs/validation.md). It reports a discrimination study
against 1,368 real prompts that the tool failed, and it is the reason claims in
this repo are phrased as *coverage* rather than *quality*. New claims about what
the score proves need new evidence.

## Dev setup

```bash
git clone https://github.com/shmindmaster/crewscore.git
cd crewscore
pip install -e ".[dev]"
pytest -q
```

## How scoring works

- Patterns live in `crewscore/scorers/structural_analysis.py` (`SCORER_MAP`).
- Scores are match counts mapped to 0–100 (see `_score_from_match_count`).
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

Be respectful. File false-positive / false-negative scoring issues with the prompt text and expected dimension.
