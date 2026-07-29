## What changed

Describe the user-facing change and whether it affects scoring, browser
parity, CLI/Action contracts, documentation, or generated artifacts.

## Validation

- [ ] Focused tests pass.
- [ ] `pytest -q` passes when shared contracts changed.
- [ ] `python scripts/export_web_engine.py` and parity tests ran when rules or
      control templates changed.
- [ ] Claims remain written-control coverage, not runtime proof or a safety
      grade.

## Scoring changes only

- [ ] Rule/control IDs, provenance, expected score delta, and validation corpus
      impact are documented.
- [ ] `CHANGELOG.md`, generated validation artifacts, and relevant docs are in
      the same change.
