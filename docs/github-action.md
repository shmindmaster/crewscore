# GitHub Action and CI integration

Canonical Action and CI guide for CrewScore. For explicit control policies and
SARIF shape, see also [policies.md](policies.md).

## GitHub Action (recommended)

CrewScore's own recurring validation runs on GitHub-hosted `ubuntu-latest`
runners, exactly like the workflow below — so this is the configuration the
project actually exercises, not an untested starting point.

If you run CrewScore on a self-hosted runner instead, apply a trust boundary
first. A self-hosted runner keeps state and credentials between jobs, so
executing pull-request code from forks on one is a compromise waiting to happen;
gate those jobs to maintainer-owned, same-repository pull requests.

### Step 1 — report-only (never fails a build)

```yaml
# .github/workflows/crewscore.yml
name: CrewScore
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write   # sticky PR comment; omitting it degrades to a warning
    steps:
      - uses: actions/checkout@v4
      - uses: shmindmaster/crewscore@v2
        with:
          scan-path: "."
```

Run this for a week. Read the sticky comments. Decide which controls your
workflow actually needs before you make anything fail.

### Step 2 — enforce named controls

```yaml
      - name: CrewScore
        id: crewscore
        uses: shmindmaster/crewscore@v2
        with:
          scan-path: "."
          # The build fails only when a named control is missing — never on
          # the coverage average. Failures surface as ::error annotations
          # naming the control and the file.
          required-controls: "human_gate.approval_required,safe_stop.stop_condition"
          sarif: "crewscore.sarif"
          # explain: "true"     # matched vs missing signals
          # pr-comment: "true"  # default on pull_request
      - name: Report
        if: always()
        run: |
          echo "score=${{ steps.crewscore.outputs.score }}"
          echo "tier=${{ steps.crewscore.outputs.tier }}"
```

### Prompt-free by default

The step echoes `--json` into the build log, writes `--summary`, and (on
`pull_request`) posts that summary as a sticky PR comment. All three are
prompt-free by default: they carry rule IDs, dimensions, status, and control
labels, never the matched substring of the file that was scanned. `sarif` is
prompt-free and is not affected by any input.

Set `include-snippets: "true"` only if you have a workflow that already parses
the `snippet` key. It is a deprecated compatibility escape hatch and will be
removed after one release.

### Optional — inline code-scanning annotations from SARIF

The SARIF report is prompt-free (control IDs and file paths, no prompt text or
snippets), so it is safe to upload to code scanning:

```yaml
      - name: Upload SARIF to code scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: crewscore.sarif
        # Requires: permissions: security-events: write
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt-file` | one of | — | Path to a single system prompt file |
| `scan-path` | one of | — | Path for `crewscore scan`. The worst score across **governed** files becomes the output |
| `threshold` | no | `""` | Optional legacy numeric gate. Prefer explicit control policies; coding-agent config is exempt |
| `max-smells` | no | `""` | Fail the step (exit 2) when any file carries more than N configuration smells. This is the gate for `AGENTS.md`-style files |
| `explain` | no | `false` | Include matched/missing signals |
| `summary` | no | `crewscore-summary.md` | Markdown path; also appended to `GITHUB_STEP_SUMMARY` |
| `pr-comment` | no | `true` | On `pull_request`, post or update a sticky comment |
| `required-controls` | no | `""` | Comma-separated public control IDs or dimensions that must be present |
| `forbid-missing` | no | `""` | Comma-separated public control IDs or dimensions that must not be missing |
| `baseline` | no | `""` | Prompt-free baseline JSON from `crewscore baseline` |
| `fail-on-regression` | no | `false` | Fail only if a baseline control disappears |
| `config` | no | `""` | Optional `.crewscore.yml` control-policy file |
| `sarif` | no | `""` | Optional destination for prompt-free SARIF 2.1.0 findings |
| `include-snippets` | no | `false` | **Deprecated.** `"true"` re-admits matched prompt substrings into the JSON log, summary, and sticky PR comment. Default keeps every machine output prompt-free; removed after one release |

Provide **either** `prompt-file` **or** `scan-path`. In scan mode the outputs
use the minimum overall across governed files only — coding-agent config is
excluded, because it is judged on configuration smells rather than this number.

### Outputs

`score` and `tier` are both the **empty string** when a scan finds no governed
files at all — a repo with only `AGENTS.md`-style config and no system prompts,
for example.

**Guard on `scored`, not on `score`.** GitHub casts `''` to `0` in numeric
comparisons, so an existing numeric comparison can mistakenly fail a run that
measured nothing. Check `steps.crewscore.outputs.scored == 'true'` before any
legacy numeric logic; new workflows should use an explicit control policy.

`summary-path` carries the markdown summary path, if one was written.

### Notes

- Sticky PR comments need `permissions: pull-requests: write`. Without it
  (fork PRs always run with a read-only token) the action emits a workflow
  warning and continues — the summary is still in the job summary. Set
  `pr-comment: "false"` to disable entirely.
- The composite action installs from the action path
  (`pip install "${{ github.action_path }}"`), so monorepo and pre-PyPI
  self-tests work with `uses: ./`.
- `@v2` is a floating major tag moved to each compatible release by the release
  workflow, so consumers pick up Action fixes without editing every workflow.
  Pin `@vX.Y.Z` instead if you want immutability.
- Any action you run executes with your workflow's token, so pin the actions in
  jobs that hold write permissions or an OIDC identity token to a full commit
  SHA, with the version in an adjacent comment keeping it reviewable:

  ```yaml
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  ```

  A mutable tag is owned by whoever publishes that action; in a privileged job,
  moving it re-points the code that holds your credentials. Add a
  `github-actions` entry to `.github/dependabot.yml` and Dependabot will keep
  both the SHA and the comment current. This repository does exactly that, and
  `tests/test_workflow_provenance.py` fails the build when a pin regresses.
- Templates: [`example-ci.yml`](../.github/workflows/example-ci.yml) and this
  repo's [self-test](../.github/workflows/crewscore-selftest.yml).

---

## CLI in CI

```yaml
# .github/workflows/crewscore-cli.yml
name: CrewScore CLI
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install crewscore
      # Example policy: choose controls that match your workflow.
      - run: crewscore scan . --json --require human_gate.approval_required,safe_stop.stop_condition
```

### Parsing the JSON yourself

**Branch on `governance_applicable` before reading `overall`.** Coding-agent
config carries no governance grade, and the field is **absent** rather than
`0`. So `jq '.overall'` yields `null`; apply a policy only after checking the
profile. An unguarded numeric legacy gate can quietly fail the build on every
`AGENTS.md` in the repo.

```bash
# single file: read a governance field only when the profile carries one
crewscore test --prompt-file ./AGENTS.md --json \
  | jq -e 'if .governance_applicable then (.overall | type == "number") else true end'

# scan: worst score across the files that carry one
crewscore scan . --json \
  | jq '[.[] | select(.governance_applicable) | .overall] | min'
```

The official Action already does this, and exposes `scored` to guard on.

---

## Recommended policy setup

Run `crewscore init .` once, review the generated prompt-free baseline and
`.crewscore.yml`, then use:

```yaml
- uses: shmindmaster/crewscore@v2
  with:
    scan-path: "."
    config: .crewscore.yml
    sarif: crewscore.sarif
```

The generated workflow stores SARIF as an artifact. The report contains
missing control IDs and file paths but no prompt text or matching snippets; use
your code-scanning provider's approved SARIF upload step if you want inline
annotations. See [policies.md](policies.md) for baseline and control details.

---

## Legacy numeric thresholds

`threshold` remains available for existing automation, but it is a count of
written-control matches, not a safety or maturity bar. New workflows should
name the controls they need with `required-controls` / `--require`, or protect
a reviewed baseline with `fail-on-regression` / `--fail-on-regression`.

If you retain a numeric gate, set it against your own files rather than the
tier ladder, and re-check it after a ruleset update (`crewscore rules --json`
reports the version). The [CHANGELOG](../CHANGELOG.md) records scoring deltas.
