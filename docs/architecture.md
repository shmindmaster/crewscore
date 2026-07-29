# Architecture

CrewScore has one source of truth for deterministic written-control matching:
`crewscore/scorers/structural_analysis.py`. The Python CLI, repository scan,
reports, Action, and generated browser engine all consume that catalog.

```
public rule catalog -> concepts (23 controls) -> deterministic matches
                                           |-> CLI / scan / Action
                                           |-> generated score-engine.js -> browser checker
                                           |-> explicit policy / SARIF (control IDs only)
```

`scripts/export_web_engine.py` regenerates `score-engine.js` after catalog or
control-template changes. The parity tests fail if the browser payload drifts
from the Python engine.

Artifact classification is intentionally separate from matching. Filenames
such as `AGENTS.md` and `CLAUDE.md` classify as coding-agent configuration and
receive advisory configuration-smell findings, never a governance score. All
other supported prompt artifacts receive the published 23-control coverage
calculation. `--profile` is the explicit override.

The browser checker is static. It keeps prompt text in page memory, and its
share fragments, analytics events, SVG cards, and downloaded reports contain
only non-content metadata or selected control IDs. See [privacy](../privacy.html)
and [validation](validation.md) for the corresponding limits.
