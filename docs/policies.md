# Control policies, regression checks, and SARIF

CrewScore's score is **written-control coverage, not a safety bar**. Use a
numeric threshold only for an intentionally legacy workflow. New CI should
protect either controls your team explicitly needs or controls that were
already written and must not disappear.

None of the policy files or SARIF output contains prompt text, matched
snippets, source URLs, or generated fixes.

## Start safely

```bash
crewscore init .
```

This creates three reviewable files:

- `.crewscore.yml` — explicit policy settings;
- `.crewscore-baseline.json` — found control IDs only, no prompt text;
- `.github/workflows/crewscore.yml` — a non-deploying pull-request check that
  stores a SARIF artifact.

`init` refuses to replace any of those files unless you pass `--force`.

## Regression checks

Record the current prompt-free state after review:

```bash
crewscore baseline . --output .crewscore-baseline.json
crewscore scan . --baseline .crewscore-baseline.json --fail-on-regression
```

The second command fails only when a control present in the baseline is no
longer detected. A newly discovered prompt with no baseline entry is reported
but does not fail; run `crewscore baseline` after reviewing the new artifact.
Baseline files are ruleset-specific evidence snapshots, not approval records.
Review and regenerate one deliberately after a ruleset change.

## Require controls explicitly

Use a public control ID for a narrow policy:

```bash
crewscore scan . --require human_gate.approval_required \
  --forbid-missing safe_stop.stop_condition
```

Or use a dimension name to require every currently published control in that
dimension:

```bash
crewscore scan . --require human_gate,safe_stop
```

These gates never apply a governance score to `AGENTS.md`/`CLAUDE.md`-class
coding-agent configuration. Those files remain subject to `--max-smells`.

## `.crewscore.yml`

`--config .crewscore.yml` reads this deliberately small schema:

```yaml
version: 1
baseline: .crewscore-baseline.json
fail_on_regression: true
required_controls:
  - human_gate.approval_required
  - safe_stop.stop_condition
forbid_missing: []
```

CLI flags add to the control lists and override the configured baseline path.
Unknown keys and invalid control IDs fail clearly rather than silently being
ignored.

## SARIF

```bash
crewscore scan . --sarif crewscore.sarif
```

The SARIF report uses one warning per missing public control and points at the
artifact file. It intentionally carries no prompt snippets because code
scanning and build artifacts often have broader retention and access than the
prompt itself. Upload `crewscore.sarif` to the code-scanning system your
repository uses, or keep it as a CI artifact.

## GitHub Action

```yaml
- uses: shmindmaster/crewscore@v2
  with:
    scan-path: .
    config: .crewscore.yml
    sarif: crewscore.sarif
```

The Action is report-only by default. Its existing `score`, `tier`, and
`scored` outputs retain their numeric compatibility. Add `required-controls`,
`baseline`, `fail-on-regression`, or `config` only when you intentionally want
one of these explicit control policies to fail the workflow.
