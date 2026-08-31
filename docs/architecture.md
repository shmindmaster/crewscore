# Architecture

CrewScore is an offline, deterministic written-control checker. It does not call
models, enforce runtime tool gates, or certify vendors.

## What it does

| Concern | Owner | Behavior |
| --- | --- | --- |
| Artifact classification | `crewscore/profiles.py` | Filename/path only — never content sniffing |
| Governance matching | `crewscore/scorers/structural_analysis.py` | 8 dimensions / 23 controls (regex) |
| Configuration smells | `crewscore/smells.py` | Advisory only; never folded into the score |
| Scoring / tiers / JSON shape | `crewscore/scoring.py` | `RULESET_ID`, result model, config vs governed branch |
| Open catalog + provenance | `crewscore/rules_catalog.py` | `crewscore rules` surface |
| Remediation templates | `crewscore/scorers/fix_patterns.py` | Text suggestions only |
| Repo discovery | `crewscore/scan.py` | `crewscore scan` |
| Scan-root containment | `crewscore/pathsafe.py` | One boundary for both discovery walks; links never followed |
| Explicit CI policy | `crewscore/policy.py` | require / baseline / regression |
| SARIF | `crewscore/sarif.py` | Prompt-free missing-control findings |
| PR/job markdown | `crewscore/summary.py` | Sticky comments / step summary |
| HTML report + badge | `crewscore/report.py` | Optional CLI artifacts |
| Browser payload | `crewscore/web_export.py` → `score-engine.js` | One generation boundary |
| Live-eval handoff | `crewscore/export_eval.py` | Writes starters; does not run Promptfoo/garak |
| Vendor diligence | `crewscore/vendor_scorecard.py` | Self-attest only; secondary |
| Metrics schema | `crewscore/metrics.py` | Privacy allowlists; parity with `analytics.js` |
| CLI orchestration | `crewscore/cli.py` | click entry for all commands |
| GitHub Action | `action.yml` | Installs package, runs `scan`/`test` |

## Data flow

```
prompt or repo path
        │
        ▼
 classify_path (profiles) ──coding_agent_config──► smells → CONFIG tier
        │                                              (no governance score)
        │ system_prompt
        ▼
 structural_analysis (23 controls)
        │
        ├── score + findings ──► CLI / JSON / summary / report / badge
        ├── missing control IDs ──► policy gate / SARIF / baseline
        ├── gaps ──► fix templates (plan or write)
        ├── gaps ──► export-eval (Promptfoo / garak handoff files)
        └── web_export ──► score-engine.js ──► browser checker
```

## Source of truth

| Contract | Authority |
| --- | --- |
| Control IDs, patterns, concepts | `structural_analysis.py` (`SCORER_MAP`, `CONCEPTS`) |
| Ruleset id | `scoring.RULESET_ID` (also re-exported from structural_analysis) |
| Dimension provenance | `rules_catalog.DIMENSION_PROVENANCE` |
| Scoring formula text | `rules_catalog.SCORING_METHOD` + this docs set |
| Fix templates | `fix_patterns.FIX_TEMPLATES` / `CONTROL_FIX_TEMPLATES` |
| Browser engine | Generated only via `python scripts/export_web_engine.py` |
| Package version | `crewscore.__version__` / `pyproject.toml` |

There is intentionally **one** browser generation boundary. Parity tests fail if
`score-engine.js` drifts from Python.

## Lean target architecture

Keep layers only where they buy a real boundary:

1. **Classify** → profile
2. **Match** → findings / smells
3. **Score / policy** → numbers, gates, SARIF
4. **Format** → human CLI, JSON, markdown, HTML, badge
5. **Orchestrate** → CLI commands and Action shell

Avoid repositories, service containers, LLM SDKs, or framework adapters until
there is a second real implementation that needs them.

## Product surfaces (all retained)

| Surface | Role |
| --- | --- |
| Primary | `test`, `scan`, `fix`, `rules`, `baseline`, `init` |
| CI | Action + policy + SARIF + summary |
| Browser | Static checker at crewscore.ai |
| Secondary | `export-eval` (live-tool handoff), `assess-vendor` (self-attest) |
| Compatibility | `agent-guard` console script alias (do not document as install name) |

## Repository layout (product code)

```
crewscore/           # installable package
  scorers/           # matching + fix templates
scripts/             # export_web_engine, validate_corpus, score_corpus
tests/               # unit + contract tests
examples/corpus/     # synthetic fixtures (not the validation corpus)
docs/                # user + methodology docs
action.yml           # composite GitHub Action
index.html + assets/ # static browser product
score-engine.js      # generated browser engine (commit after pattern changes)
```

Local-only / generated paths (not product architecture): `dist/`,
`node_modules/`, `test-results/`, `.corpus-cache/`, `_production/`,
`_product-experience/` (see `.gitignore`).

## Security and privacy boundaries

- Core CLI path is offline; no network required to score.
- Discovery stays inside the caller-selected root (`crewscore/pathsafe.py`):
  the root is resolved once and every candidate must resolve inside it.
  Symlinks and junctions are never followed, so a linked directory is not
  descended - which also makes link cycles impossible - and a linked file is
  never opened. Refusals are reported on stderr, never as scan rows.
- SARIF, baselines, and policy files carry **control IDs**, not prompt text.
- Browser scoring keeps prompt text in page memory; share/export payloads are
  metadata / control IDs. Shared result links are unsigned local fragments, so
  they are validated as untrusted input before any number is rendered — see
  [Shared result links](development.md#shared-result-links). Analytics use an
  allowlisted event schema (`metrics.py` ↔ `analytics.js`).
- Vendor checklist and LinkedIn copy are self-attested summaries, not audits.

## Related docs

- [Scoring and controls](scoring-and-controls.md)
- [Validation](validation.md)
- [CLI](cli.md)
- [GitHub Action](github-action.md)
- [Development](development.md)
- [Live eval handoff](next-steps-eval.md)
