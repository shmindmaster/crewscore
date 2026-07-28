<div align="center">

# CrewScore

### Free structural score for AI agent prompts — no signup, no install required

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![PyPI](https://img.shields.io/badge/PyPI-crewscore-blue.svg)](https://pypi.org/project/crewscore/)
[![GitHub Action](https://img.shields.io/badge/Action-shmindmaster%2Fcrewscore%40v1-blue.svg)](https://github.com/shmindmaster/crewscore/blob/main/action.yml)

<br/>

<!-- Hero demo: real product capture (weak prompt → score → plan → apply → export) -->
![CrewScore hero demo — weak prompt → structural score → plan fix → apply → export](docs/hero-demo.gif)

**[~25s end-to-end](docs/hero-demo.mp4)** · try live: **[crewscore.ai](https://crewscore.ai)** · re-record: `node scripts/record-hero-demo.mjs --public-gif`

<br/>

**Everyone (zero friction):** open **[crewscore.ai](https://crewscore.ai)** → paste prompt or pick a template → score → **fix gaps** → share.

**Teams / CI:** `pip install crewscore` · GitHub Action `shmindmaster/crewscore@v1`

```
$ pip install crewscore
$ crewscore scan .

  path                              overall  tier
  --------------------------------  -------  ---------------------------
  ./AGENTS.md                            42  STRUCTURAL: CRITICAL GAPS
  ./agents/system-prompt.md              61  STRUCTURAL: WEAK

  worst: 42  (gate with --threshold)
```

Score the **text** of your agent instructions. Fix gaps. Gate CI when scores drop.  
Structural hygiene only — **not a red-team**, not a certification.

[Install](#install) · [Usage](#usage) · [Demo](#demo) · [Scoring charter](#scoring-charter) · [Share](#share-your-score) · [How scoring works](#how-scoring-works) · [CI](#ci-integration) · [After CrewScore](#after-crewscore) · [Limits](#what-this-is-and-is-not)

</div>

---

## The problem

You shipped an agent that works in a demo. Before production you still need to ask:

- Does the prompt resist obvious injection / override language?
- Does it forbid fabricating citations and force “I don’t know”?
- Are writes, sends, and publishes gated on human approval?
- Is there any cost, audit, or compliance language at all?

Most teams never inspect those instructions systematically. **CrewScore** does a fast structural scan and can append proven guardrail patterns.

---

## What this is (and is not)

| Is | Is not |
|----|--------|
| Offline structural scan of system-prompt text | Live adversarial LLM red-teaming |
| Fix mode that appends guardrail sections | Proof that the runtime will obey the text |
| JSON output + exit threshold for CI | LangGraph / CrewAI graph execution analysis |
| Optional vendor self-attest checklist | Independent security certification |

Scores reflect **prompt-text signals**. They are a useful smoke test, not a guarantee of runtime safety.

> **Name note:** PyPI package `agent-guard` is an unrelated third-party CrewAI monitoring library. This project is **CrewScore** (`pip install crewscore`). The CLI also accepts the legacy alias `agent-guard` after install.

---

## Demo

The README hero is a **real browser capture** of the product (not a mock):

1. Weak demo prompt  
2. Structural score (~0/100 critical gaps)  
3. Inspect dimensions  
4. Plan fix → apply templates  
5. Export / share  

| Asset | Use |
| --- | --- |
| [docs/hero-demo.gif](docs/hero-demo.gif) | README / embeds (autoplay loop) |
| [docs/hero-demo.mp4](docs/hero-demo.mp4) | X, LinkedIn, Reddit, Show HN first comment |
| [crewscore.ai](https://crewscore.ai) | Live interactive demo (no install) |

```bash
# regenerate from the real static site in this repo
node scripts/record-hero-demo.mjs --public-gif
```

Requires Playwright + ffmpeg (script reuses a portfolio Playwright install if present).

---

## Scoring charter (not a black box)

Honest principles we ship by:

1. CrewScore measures **presence of hygiene signals in text**, not agent behavior.
2. Scores are **rule-pack versioned** (`crewscore-hygiene@0.2.3`) and **deterministic** — no LLM, no hidden model.
3. **Every rule is public.** List them anytime:
   ```bash
   crewscore rules              # human: formula + every rule_id + regex
   crewscore rules --json       # machine-readable full catalog
   ```
4. Findings show **open `rule_id`s**, match snippets, or explicit missing labels (default in CLI and JSON).
5. `fix` improves **text coverage**, not runtime safety; template boilerplate triggers a warning.
6. We never call a score a **certification**, **audit**, or **red-team result**.
7. When in doubt, **under-score** rather than inflate.
8. Source of truth: [`crewscore/scorers/structural_analysis.py`](crewscore/scorers/structural_analysis.py).

See also [docs/next-steps-eval.md](docs/next-steps-eval.md) for when to graduate to live eval tools.

---

## Install

```bash
pip install crewscore

# from source (development)
pip install -e ".[dev]"
```

No API key for structural mode.

---

## Usage

### Scan a repo for agent prompts (recommended)

Discover and score likely agent instruction files (`AGENTS.md`, `CLAUDE.md`, `system-prompt.md`, paths under `prompts/` / `agents/`, and similar):

```bash
crewscore scan .
crewscore scan ./agents --json
crewscore scan . --threshold 50
crewscore scan . --json --threshold 50
crewscore scan . --summary crewscore-summary.md
crewscore test --prompt-file ./AGENTS.md --summary crewscore-summary.md

# Synthetic demo gradient (bare → hardened)
crewscore scan examples/corpus
```

- Prints a table of path → overall → tier (JSON with `--json`).
- `--threshold N` exits `2` if **any** file scores below `N`.
- `--summary PATH` writes transparent PR/job markdown (formula + open rule IDs for single-file; table for scan).
- Exit `1` if no candidate files are found.
- Skips `node_modules`, `.git`, `venv`, `dist`, `__pycache__`, `.venv`.
- Demo fixtures: [examples/corpus/](examples/corpus/) + [LEADERBOARD.md](examples/corpus/LEADERBOARD.md).

Use this as the default CI gate for monorepos with multiple agent artifacts.

### Score a single system prompt

```bash
crewscore test --prompt "You are a customer service agent for..."
crewscore test --prompt-file ./my-agent/system-prompt.md
crewscore test --prompt-file ./my-agent/system-prompt.md --json
crewscore test --prompt-file ./my-agent/system-prompt.md --json --threshold 50
```

`--threshold N` exits with code `2` when overall score is below `N` (CI gate).

### Share your score

Export a self-contained HTML report and an SVG badge after scoring:

```bash
crewscore test --prompt-file ./system-prompt.md --report report.html --badge crewscore.svg
```

Embed the badge in a README or PR description (path relative to your repo):

```markdown
![CrewScore](./crewscore.svg)
```

Or point CI at a committed badge path after generating it in a workflow step:

```markdown
![CrewScore](./badges/crewscore.svg)
```

Human mode also prints a one-line share blurb with your overall score and [crewscore.ai](https://crewscore.ai). Reports are structural-scan artifacts only — not runtime proof of safety.

### Apply guardrail patterns

```bash
# plan only — list dimensions that would be fixed (no file write)
crewscore fix --prompt-file ./system-prompt.md --plan
# alias:
crewscore fix --prompt-file ./system-prompt.md --dry-run

# print enhanced prompt (stdout only)
crewscore fix --prompt-file ./system-prompt.md

# write in place and show score delta
crewscore fix --prompt-file ./system-prompt.md --apply

# write to a new file
crewscore fix --prompt-file ./system-prompt.md --output ./system-prompt-guarded.md

# machine-readable summary
crewscore fix --prompt-file ./system-prompt.md --apply --json
# plan as JSON (fixes_planned, written: false)
crewscore fix --prompt-file ./system-prompt.md --plan --json
```

`--plan` / `--dry-run` is mutually exclusive with `--apply` and `--output`. These are **prompt text templates**. They can raise the structural score without changing runtime behavior — wire matching controls (tool gates, logging, budgets) in your application.

### Vendor checklist (self-attest, secondary)

Optional procurement diligence checklist — not the main product path:

```bash
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y"
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json
```

Answers are `y` / `n` / `dk` for each of 10 diligence questions. Self-attested only — not an audit.

### Browser demo

Open **[crewscore.ai](https://crewscore.ai)** (or `index.html` locally) for a zero-install structural scan, one-click fix, and templates. Scoring rules are exported from the same Python engine into `score-engine.js` so browser and CLI stay in lockstep.

---

## How scoring works

**One engine:** Python CLI and the [crewscore.ai](https://crewscore.ai) site use the same patterns. The browser loads `score-engine.js`, generated from Python via `scripts/export_web_engine.py` (CI fails if it drifts).

**Formula (fully public):**

- Per dimension: count how many open rules’ regexes match (case-insensitive).  
  `score = 0` if no matches, else `min(100, round(15 + 85 × matches / total_rules))`.
- Overall: integer mean of the 8 dimension scores.
- Inspect any rule: `crewscore rules` / `crewscore rules --json`.

Eight dimensions, equal weight, each 0–100:

| Dimension | What the scanner looks for |
|-----------|----------------------------|
| Prompt Injection Resistance | Reject-override / do-not-reveal-system / jailbreak language |
| Hallucination Guardrails | No fabrication, “I don’t know”, grounded-only claims |
| Source Citation | Claims must cite sources / evidence |
| Cost Runaway Protection | Token/budget/max-length limits |
| Human-in-the-Loop Gates | Approval before send/write/publish |
| Safe-Stop Behavior | Halt when evidence missing or uncertain |
| Audit Trail | Log decisions / immutable trail language |
| Compliance Readiness | HIPAA/SOC2/GDPR/EU AI Act style handling language |

### Score tiers (structural framing)

| Score | Verdict |
|-------|---------|
| 90–100 | `STRUCTURAL: STRONG` |
| 70–89 | `STRUCTURAL: OK WITH GAPS` |
| 50–69 | `STRUCTURAL: WEAK` |
| 0–49 | `STRUCTURAL: CRITICAL GAPS` |

Labels describe **prompt-text coverage**, not production certification.

---

## CI integration

### Official GitHub Action (recommended)

One YAML step — no manual pip ritual:

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
        uses: shmindmaster/crewscore@v1
        with:
          # Prefer repo scan when you have multiple agent artifacts:
          # scan-path: "."
          prompt-file: ./agents/system-prompt.md
          threshold: "50"
          # explain: "true"   # optional: matched vs missing signals
          # pr-comment: "true"  # default: sticky PR comment on pull_request
          # summary: crewscore-summary.md
      - name: Report
        if: always()
        run: |
          echo "score=${{ steps.crewscore.outputs.score }}"
          echo "tier=${{ steps.crewscore.outputs.tier }}"
```

**Inputs**

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt-file` | one of | — | Path to a single system prompt file |
| `scan-path` | one of | — | Path for `crewscore scan` (worst score becomes the output) |
| `threshold` | no | `50` | Fail the step (exit 2) when overall score is below this |
| `explain` | no | `false` | Pass `true` to include matched/missing signals |
| `summary` | no | `crewscore-summary.md` | Markdown path (also appends to `GITHUB_STEP_SUMMARY`) |
| `pr-comment` | no | `true` | On `pull_request`, post/update a sticky comment with the summary |

Provide **either** `prompt-file` **or** `scan-path` (not neither). For scan mode, outputs use the **minimum** overall across discovered files.

**Outputs:** `score` (0–100), `tier` (label string), `summary-path` (markdown file if written).

Sticky PR comments need `permissions: pull-requests: write` on the job. Set `pr-comment: "false"` to disable.

The composite action installs CrewScore from the action path (`pip install "${{ github.action_path }}"`), so monorepo / pre-PyPI self-tests work with `uses: ./`.

`uses: shmindmaster/crewscore@v1` requires a floating major tag `v1` on the release commit (in addition to the immutable `vX.Y.Z` tag). Maintainers create or move `v1` after each compatible release so workflows pick up compatible Action fixes without editing every consumer.

See [`.github/workflows/example-ci.yml`](.github/workflows/example-ci.yml) for a documented consumer template and [`.github/workflows/crewscore-selftest.yml`](.github/workflows/crewscore-selftest.yml) for this repo’s smoke self-test.

### CLI in CI

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
      # or single file:
      # - run: crewscore test --prompt-file ./agents/system-prompt.md --json --threshold 50
```

Or parse JSON yourself:

```bash
SCORE=$(crewscore test --prompt-file ./agents/system-prompt.md --json | jq '.overall')
```

---

## After CrewScore

CrewScore is the cheap lint / structural pre-gate. When you need **live** behavior:

| Need | Tool |
|------|------|
| Prompt eval suites, YAML scenarios, CI assertions | [Promptfoo](https://www.promptfoo.dev/) |
| LLM vulnerability / jailbreak scanning | [garak](https://github.com/NVIDIA/garak) (NVIDIA) |
| Deeper agent red-team | Promptfoo agents / PyRIT / your own harness |

Structural scores do **not** measure jailbreak resistance or multi-turn tool abuse. Use those tools after the prompt text has basic hygiene. Details: [docs/next-steps-eval.md](docs/next-steps-eval.md).

Generate starter stubs (does **not** run live evals):

```bash
crewscore export-eval --prompt-file ./agents/system-prompt.md -o ./crewscore-eval
# → promptfooconfig.yaml + README-EVAL.md (Promptfoo + garak notes)
```

---

## Fix patterns

When dimensions score below threshold, `crewscore fix` appends production-style guardrail sections for:

- Injection defense
- Anti-hallucination
- Citation requirements
- Cost governance
- Human gates
- Safe-stop
- Audit trail
- Compliance / data protection

These are **prompt text templates**. Wire matching runtime controls (tool gates, logging, budgets) in your application.

---

## Development

```bash
git clone https://github.com/shmindmaster/crewscore.git
cd crewscore
pip install -e ".[dev]"
pytest
crewscore test --prompt "You are a helpful assistant"
```

See [AGENTS.md](AGENTS.md) for agent/contributor operating notes.

---

## Roadmap (not implemented yet)

- Framework adapters that extract prompts from LangGraph / CrewAI / AutoGen graphs
- Optional live adversarial testing (post-traction; not the default path)

---

## License

MIT.
