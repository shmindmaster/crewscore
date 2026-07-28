<div align="center">

# CrewScore

### Free structural score for AI agent prompts — no signup, no install required

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![PyPI](https://img.shields.io/badge/PyPI-crewscore-blue.svg)](https://pypi.org/project/crewscore/)
[![GitHub Action](https://img.shields.io/badge/Action-shmindmaster%2Fcrewscore%40v1-blue.svg)](https://github.com/shmindmaster/crewscore/blob/main/action.yml)

<br/>

![CrewScore — paste a weak prompt, score it, plan fixes, export](docs/hero-demo.gif)

**Try it live (no install):** [crewscore.ai](https://crewscore.ai) · [video](docs/hero-demo.mp4)

<br/>

```bash
pip install crewscore
crewscore test --prompt "You are a helpful assistant."
# → 0/100  STRUCTURAL: CRITICAL GAPS  ·  8 dimensions  ·  offline, no API key
```

**CI:** `crewscore scan . --threshold 50` · Action `shmindmaster/crewscore@v1`  
Structural hygiene only — **not a red-team**, not a certification.

[Install](#install) · [Usage](#usage) · [Scoring charter](#scoring-charter) · [Two rulesets](#two-artifacts-two-rulesets) · [Config smells](#configuration-smells) · [How scoring works](#how-scoring-works) · [What changed](#what-changed-in-030) · [CI](#ci-integration) · [Limits](#what-this-is-and-is-not)

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

## Scoring charter (not a black box)

Honest principles we ship by:

1. CrewScore measures **presence of hygiene signals in text**, not agent behavior.
2. Scores are **rule-pack versioned** (`crewscore-hygiene@0.3.0`) and **deterministic** — no LLM, no hidden model.
3. **Every rule is public.** List them anytime:
   ```bash
   crewscore rules              # human: formula + provenance + every rule_id + regex
   crewscore rules --json       # machine-readable full catalog
   ```
4. Findings show **open `rule_id`s**, match snippets, or explicit missing labels (default in CLI and JSON).
5. **Every rule declares where it came from.** Each dimension is graded `evidence-backed`, `plausible`, or `author-intuition`, with citations. Three of the eight are evidence-backed; one (Compliance Readiness) is explicitly author-intuition, because detecting the word "HIPAA" is not detecting compliance.
6. **Length is never a score.** Long files cost tokens on every run — see [configuration smells](#configuration-smells) below.
7. `fix` improves **text coverage**, not runtime safety; it reports its own context cost, and template boilerplate triggers a warning.
8. We never call a score a **certification**, **audit**, or **red-team result**.
9. When in doubt, **under-score** rather than inflate.
10. Source of truth: [`crewscore/scorers/structural_analysis.py`](crewscore/scorers/structural_analysis.py).

> **Changed in `0.3.0`:** CrewScore used to award up to +10 per dimension for prompts over 500 words. That rewarded the exact thing the research penalizes — and it was never in the published formula. It is gone. See [what changed and why](#what-changed-in-030).

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
crewscore scan . --threshold 50            # gates system prompts
crewscore scan . --max-smells 0            # gates coding-agent config
crewscore scan . --json --threshold 50
crewscore scan . --summary crewscore-summary.md
crewscore test --prompt-file ./AGENTS.md --summary crewscore-summary.md

# Synthetic demo gradient (bare → hardened)
crewscore scan examples/corpus
```

- Prints a table of path → artifact → score → verdict (JSON with `--json`).
- `--threshold N` exits `2` if any **system prompt** scores below `N`. [Coding-agent config is exempt](#two-artifacts-two-rulesets) — it isn't judged on that number.
- `--max-smells N` exits `2` if any file has more than `N` configuration smells.
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

## Two artifacts, two rulesets

CrewScore judges two different kinds of file, and it will tell you which one it thinks it's looking at.

| Artifact | Examples | Judged on |
|----------|----------|-----------|
| **Coding-agent config** | `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/*.mdc`, `copilot-instructions.md` | [Configuration smells](#configuration-smells) |
| **Agent system prompt** | `system-prompt.md`, anything under `prompts/` or `agents/`, pasted text | The [8 governance dimensions](#how-scoring-works) |

Why: a file that says *"Always use pnpm"* and *"Build with `make build`"* is telling a coding agent how to work in your repo. It has no reason to contain HIPAA language or human-approval gates, and scoring it against those is a category error.

We know the size of that error because we measured it. Against the 100 most-starred repos with an `AGENTS.md` ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828) corpus), the governance ruleset scored them at a **median of 0/100**, with all 100 in the worst tier. A scale where the entire real-world population fails carries no information. So config files no longer get a governance grade at all — they get a smell verdict.

```bash
crewscore test --prompt-file AGENTS.md
# → CONFIG: NO SMELLS DETECTED  (not "0/100 CRITICAL GAPS")

crewscore test --prompt-file ./agents/system-prompt.md
# → OVERALL SCORE: 87/100  STRUCTURAL: OK WITH GAPS
```

Override the detection with `--profile system_prompt` or `--profile coding_agent_config` when your filenames don't follow convention.

**In CI:** `--threshold N` gates system prompts and is ignored for config files; `--max-smells N` gates config files.

---

## Configuration smells

Alongside the score, CrewScore reports **configuration smells** — problems in the *shape* of an instruction file rather than its content. These come from a published, peer-reviewed catalog: [*Configuration Smells in AGENTS.md Files*](https://arxiv.org/abs/2606.15828) (dos Santos et al., 2026), which found **91 of 100** popular open-source projects carried at least one.

CrewScore implements the three that can be detected **offline and deterministically**:

| Smell | Heuristic | Found in |
|-------|-----------|----------|
| **Context Bloat** | ≥ 200 lines | 42% of studied projects |
| **Lint Leakage** | Style rules a configured linter already enforces | 62% — the most common |
| **Init Fossilization** | Tracked by git with exactly one commit — never revised | 24% |

The paper's other three smells (Skill Leakage, Blind References, Conflicting Instructions) are detected with an LLM. CrewScore does not implement them: it would rather ship three honest detectors than six approximate ones.

**Lint Leakage is an approximation** and says so in its output. The paper uses an LLM to judge whether guidance duplicates tooling; CrewScore requires two mechanical conditions instead — style-rule language in the file *and* a linter config in the repo. That is narrower than the paper's detector and will miss cases it catches.

**Known limitation:** Init Fossilization is a commit-count heuristic, so a deliberately static file — a test fixture, a vendored example — is flagged the same as a genuinely stale config. The heuristic cannot tell "never needed revising" from "never got revised." Treat it as a prompt to look, not a verdict.

Smells are **advisory. They never change the score.** Folding them in would silently change what every existing `--threshold N` means in someone's CI. Whether they *should* affect the score is a question for corpus validation, not something to slip into a patch release.

---

## What changed in 0.3.0

Four defects, all found by testing CrewScore against the published research rather than waiting for someone else to.

**0. `AGENTS.md` files were being judged by the wrong ruleset.** Validated against the [arXiv:2606.15828](https://arxiv.org/abs/2606.15828) corpus of the 100 most-starred repos with an agent config file, CrewScore scored them at a median of **0/100** — all 100 in the worst tier. `crewscore scan` targeted exactly those files by default, so the headline command pointed the governance ruleset at the one artifact it can't assess. Fixed by [splitting the rulesets](#two-artifacts-two-rulesets): 0 of those 100 files now receive a governance grade, and the 42 flagged for Context Bloat match the paper's labels exactly.

**0b. Four rules were matching ordinary developer prose.** Measured on the same corpus: `compliance.01` matched `phi` *inside "cryptographic"* (19/100 files); `injection.05` matched *dependency injection* (19/100); `audit.02` matched bare `logging` (30/100); `citation.01`/`.05` matched `reference` and any numbered list containing "refer" (83 hits). All narrowed, with regression tests built from the exact offending strings. Roughly **70% of the apparent signal on real files was noise**.

**1. The length bonus is gone.** CrewScore awarded up to +10 per dimension for prompts over 500 words. That rewarded length — and length is a cost, not a virtue: files at or over 200 lines are Context Bloat, and [Gloaguen et al.](https://arxiv.org/abs/2602.11988) measured **>20% higher inference cost** from context files with **no gain in task success**. It was also never in the published formula, so the documented formula did not match the code. Both are fixed: the formula in this README is now the whole formula.

**2. `fix` no longer pads.** It used to turn a one-line prompt into 79 lines of generic boilerplate — consuming ~40% of the 200-line budget in one command — and score it 46 points higher for the privilege. Templates are now roughly half the size, and `fix` reports its own context cost:

```
Context cost: +44 lines (1 -> 45). Every line is re-read on every run.
WARNING: generic_dominates: added 44 lines of generic guardrail text to 1 line
         of project-specific content.
```

The remaining honest caveat: these templates are still **generic**, and the measured value of an instruction file lies in project-specific, non-standard practice. Specialize them; don't ship them verbatim.

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
| `threshold` | no | `50` | Fail the step (exit 2) when a **system prompt** scores below this. Coding-agent config is exempt — see [two rulesets](#two-artifacts-two-rulesets) |
| `max-smells` | no | `""` | Fail the step (exit 2) when any file has more than N configuration smells. This is the gate for `AGENTS.md`-style files |
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
| Prompt eval suites, YAML scenarios, CI assertions | [Promptfoo](https://www.promptfoo.dev/) (acquired by OpenAI, Mar 2026; still open source) |
| LLM vulnerability / jailbreak scanning | [garak](https://github.com/NVIDIA/garak) (NVIDIA) |
| Deeper agent red-team | Promptfoo agents / PyRIT / your own harness |

Structural scores do **not** measure jailbreak resistance or multi-turn tool abuse. Use those tools after the prompt text has basic hygiene. Details: [docs/next-steps-eval.md](docs/next-steps-eval.md).

### Other tools in this lane

CrewScore is not the only static linter for agent instruction files, and pretending otherwise would be the fastest way to lose your trust:

| Tool | What it asks | Where it differs |
|------|--------------|------------------|
| [AgentLinter](https://github.com/seojoonkim/agentlinter) | *"Will this file make the coding agent work well?"* | npm/`npx`, weighted dimensions, cross-file contradiction detection across a whole workspace |
| [lintlang](https://github.com/hermes-labs-ai/lintlang) | Static gating for agent configs | Zero-LLM CI linting |
| **CrewScore** | *"Will this agent hurt someone in production?"* | Governance lens (injection, human gates, audit, compliance), plus offline detection of published configuration smells |

If you want agent-config *craft* — clarity, structure, memory layout — AgentLinter is aimed squarely at that and is worth your time. CrewScore's lens is production governance. They are complementary, and running both is reasonable.

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
