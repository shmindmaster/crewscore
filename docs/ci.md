# CI integration

## GitHub Action (recommended)

CrewScore's own recurring validation runs on its private DigitalOcean runner
labels `[self-hosted, Linux, X64, sh-runner, docker]`; fork-authored pull
requests are refused before reaching that persistent host. The workflow below
uses a GitHub-hosted runner because it is a copy-paste starting point for your
own repository. Use your own isolated self-hosted labels only after applying
the same fork boundary.

```yaml
# .github/workflows/crewscore.yml
name: CrewScore
on: [pull_request]
jobs:
  score:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write   # sticky PR comment with open rule findings
    steps:
      - uses: actions/checkout@v4
      - name: CrewScore
        id: crewscore
        uses: shmindmaster/crewscore@v2
        with:
          # Prefer a repo scan when you have multiple agent artifacts.
          # The Action is report-only by default: use explicit public controls
          # or regressions, not the coverage average, when failing CI.
          scan-path: "."
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

Provide **either** `prompt-file` **or** `scan-path`. In scan mode the outputs
use the minimum overall across governed files only — coding-agent config is
excluded, because it is judged on configuration smells rather than this number.

### Outputs

`score` and `tier` are both the **empty string** when a scan finds no governed
files at all — a repo with only `AGENTS.md`-style config and no system prompts,
for example.

**Guard on `scored`, not on `score`.** GitHub casts `''` to `0` in numeric
comparisons, so `if: outputs.score < 50` is true for a run that measured
nothing:

```yaml
if: steps.crewscore.outputs.scored == 'true' && steps.crewscore.outputs.score < 50
```

`summary-path` carries the markdown summary path, if one was written.

### Notes

- Sticky PR comments need `permissions: pull-requests: write`. Set
  `pr-comment: "false"` to disable.
- The composite action installs from the action path
  (`pip install "${{ github.action_path }}"`), so monorepo and pre-PyPI
  self-tests work with `uses: ./`.
- `@v2` is a floating major tag moved to each compatible release by the release
  workflow, so consumers pick up Action fixes without editing every workflow.
  Pin `@vX.Y.Z` instead if you want immutability.
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
      - run: crewscore scan . --json --threshold 50
```

### Parsing the JSON yourself

**Branch on `governance_applicable` before reading `overall`.** Coding-agent
config carries no governance grade, and the field is **absent** rather than
`0`. So `jq '.overall'` yields `null`, and `jq -e '.overall >= 50'` prints
`false` and **exits 1** — it does not error. An unguarded gate quietly fails
the build on every `AGENTS.md` in the repo.

```bash
# single file: score it only if it is judged on the governance score
crewscore test --prompt-file ./AGENTS.md --json \
  | jq -e 'if .governance_applicable then .overall >= 50 else true end'

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

## Choosing a threshold

Set it against what your files actually score, not against the tier ladder.
Run `crewscore scan .` first and pick a number just under your current worst
governed file, then raise it as you close gaps.

Scores are versioned by ruleset (`crewscore rules --json` reports which). A
ruleset bump can move every score, so re-check the threshold after upgrading —
the [CHANGELOG](../CHANGELOG.md) states the delta for any release that changes
scoring.
