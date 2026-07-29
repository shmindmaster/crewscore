# Development

How to work on CrewScore locally, keep the browser engine in lockstep, and ship
honest changes.

## Setup

```bash
git clone https://github.com/shmindmaster/crewscore.git
cd crewscore
pip install -e ".[dev]"
pytest -q
```

Runtime dependencies stay intentionally small: **click** and **rich**. Dev extra
adds **pytest** and **pyyaml** (Action/workflow YAML contracts only).

Optional browser tests (static site):

```bash
npm ci --include=dev
npx playwright install chromium
npm run test:web
```

## Commands you will use

```bash
# package CLI (editable install)
crewscore scan .
crewscore test --prompt-file examples/corpus/prompts/01-bare-assistant.md --explain
crewscore rules --concepts
crewscore export-eval --prompt "You are helpful." -o ./crewscore-eval
crewscore assess-vendor --name "Acme" --answers "y,y,n,dk,y,y,n,y,n,y" --json

# after any pattern / fix-template / concept change
python scripts/export_web_engine.py
pytest tests/test_web_engine.py -q

# full suite
pytest -q

# synthetic demo fixtures
python scripts/score_corpus.py

# validation corpus (network + cache; see docs/validation-corpus.md)
python scripts/validate_corpus.py
```

## Adding a detection rule

1. Add a regex to the right list in `crewscore/scorers/structural_analysis.py`.
2. Group it under an existing control in `CONCEPTS` (or propose a new control
   with scoring governance — [scoring-and-controls.md](scoring-and-controls.md)).
3. Add/adjust unit tests in `tests/test_structural_analysis.py` or
   `tests/test_explain.py`.
4. Run `python scripts/export_web_engine.py` and commit `score-engine.js`.
5. Run `pytest -q`.

Adding a synonym for a control that is already covered **changes no score** —
that is deliberate.

## Adding a fix template

Edit `crewscore/scorers/fix_patterns.py` (`FIX_TEMPLATES` and/or
`CONTROL_FIX_TEMPLATES`). Re-export the web engine if the browser should show
the new text.

## Public contracts

Treat these as the public surface while pre-1.0:

- CLI commands and flags
- `--json` payload shape (especially `governance_applicable` branching)
- GitHub Action inputs/outputs (`action.yml`)
- Ruleset id (`crewscore-hygiene@…`)
- Generated `score-engine.js` parity with Python

Breaking any of them needs a minor version bump and CHANGELOG entry.

## Media and demo assets

| Asset | Purpose | Policy |
| --- | --- | --- |
| `docs/demo.svg` | Lightweight README/diagram asset | Keep in repo |
| `docs/social-card.png` | OG/social preview | Keep in repo |
| `docs/hero-demo.gif`, `docs/hero-demo.mp4` | Marketing hero motion | Keep for product demo; large binaries (~3.4 MB). Prefer SVG/poster for new embeds when possible |
| `demo/release-demo/` | Storyboard / truth sheet for release videos | Keep; not part of the Python package |
| `scripts/demo/` | Capture/render helpers for release demos | Keep; optional Node pipeline |

Do not commit local capture outputs under `_production/` (gitignored).

## Packaging and release

- Build backend: hatchling (`pyproject.toml`)
- Console script: `crewscore` (legacy alias `agent-guard` remains for compatibility; never document `pip install agent-guard`)
- Release workflow: `.github/workflows/release.yml` (PyPI + tag maintenance)
- Supported Python: 3.11, 3.12, 3.13

## Honesty

Before editing claims about what the score proves, read
[validation.md](validation.md). Do not document unimplemented framework loaders
or live adversarial modes as shipping features.

## Related

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [AGENTS.md](../AGENTS.md) — agent operating constraints
- [Architecture](architecture.md)
- [Scoring and controls](scoring-and-controls.md)
