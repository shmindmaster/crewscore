# CrewScore runnable quickstart

From the repository root:

```bash
pip install -e ".[dev]"
crewscore scan examples/quickstart --json
crewscore baseline examples/quickstart --output examples/quickstart/.crewscore-baseline.json
crewscore scan examples/quickstart --baseline examples/quickstart/.crewscore-baseline.json --fail-on-regression
```

The baseline contains only the artifact path and found control IDs. It does not
store this prompt text. The example demonstrates written-control coverage, not
runtime safety or tool enforcement.
