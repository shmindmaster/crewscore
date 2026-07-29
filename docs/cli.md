# CLI reference

Every command is offline and deterministic. No API key, no LLM.

```bash
pip install crewscore
```

---

## `scan` — find and score agent prompts in a repo

Discovers likely agent instruction files (`AGENTS.md`, `CLAUDE.md`,
`system-prompt.md`, paths under `prompts/` or `agents/`, and similar).

```bash
crewscore scan .
crewscore scan ./agents --json
crewscore scan . --threshold 50            # gates system prompts
crewscore scan . --max-smells 0            # gates coding-agent config
crewscore scan . --summary crewscore-summary.md

# synthetic demo gradient (bare -> hardened)
crewscore scan examples/corpus
```

- Prints path → artifact → score → verdict (JSON with `--json`).
- `--threshold N` exits `2` if any **system prompt** scores below `N`.
  [Coding-agent config is exempt](../README.md#two-artifacts-two-rulesets) — it
  is not judged on that number.
- `--max-smells N` exits `2` if any file carries more than `N` configuration
  smells.
- `--summary PATH` writes PR/job markdown (formula plus open rule IDs for a
  single file; a table for a scan).
- Exits `1` if no candidate files are found.
- Skips `node_modules`, `.git`, `venv`, `.venv`, `dist`, `__pycache__`.

This is the default CI gate for repos with more than one agent artifact.

---

## `test` — score a single prompt

```bash
crewscore test --prompt "You are a customer service agent for..."
crewscore test --prompt-file ./my-agent/system-prompt.md
crewscore test --prompt-file ./my-agent/system-prompt.md --json
crewscore test --prompt-file ./my-agent/system-prompt.md --json --threshold 50
```

`--threshold N` exits `2` when the overall score is below `N`.

### Share a result

```bash
crewscore test --prompt-file ./system-prompt.md \
  --report report.html --badge crewscore.svg
```

Embed the badge (path relative to your repo):

```markdown
![CrewScore](./crewscore.svg)
```

Human mode also prints a one-line share blurb. Reports are structural-scan
artifacts — not runtime proof of anything.

---

## `rules` — the whole catalog, open

```bash
crewscore rules              # formula, provenance, every rule_id and regex
crewscore rules --concepts   # the controls each dimension scores on
crewscore rules --json       # machine-readable catalog
crewscore rules -d injection # one dimension
```

`--concepts` is worth knowing about: a dimension scores on how many of its
**controls** your prompt states, and several rules can be alternative phrasings
of one control. That grouping is the denominator of every score, so it ships as
data rather than living inside the scorer.

---

## `fix` — append guardrail templates

```bash
# plan only, no file written
crewscore fix --prompt-file ./system-prompt.md --plan

# print the enhanced prompt to stdout
crewscore fix --prompt-file ./system-prompt.md

# write in place and show the score delta
crewscore fix --prompt-file ./system-prompt.md --apply

# write somewhere else
crewscore fix --prompt-file ./system-prompt.md --output ./system-prompt-guarded.md

# machine-readable
crewscore fix --prompt-file ./system-prompt.md --apply --json
crewscore fix --prompt-file ./system-prompt.md --plan --json
```

`--plan` (alias `--dry-run`) is mutually exclusive with `--apply` and
`--output`.

These are **prompt text templates**. They raise text coverage without changing
runtime behaviour — wire the matching controls (tool gates, logging, budgets)
in your application. CrewScore flags its own output as template boilerplate
when it dominates a file.

Templates exist for all eight dimensions: injection defense, anti-hallucination,
citation requirements, cost governance, human gates, safe-stop, audit trail, and
compliance / data protection.

**Exits `1` on coding-agent config.** `fix` refuses to write governance
templates into an `AGENTS.md`-class file (`--json`: `{"refused": true, ...}`).
A loop treating any non-zero exit as fatal will stop there — skip those paths,
or pass `--profile system_prompt` to force it. Forced runs report
`"forced_governance_write": true`.

---

## `export-eval` — starter stubs for live eval tools

Does **not** run live evals.

```bash
crewscore export-eval --prompt-file ./agents/system-prompt.md -o ./crewscore-eval
# -> promptfooconfig.yaml + README-EVAL.md (Promptfoo + garak notes)
```

See [next-steps-eval.md](next-steps-eval.md).

---

## `assess-vendor` — procurement checklist (secondary)

Self-attested only. Not an audit, and not the main product path.

```bash
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y"
crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y" --json
```

Answers are `y` / `n` / `dk` for each of 10 diligence questions.

---

## Profiles

CrewScore judges two kinds of file and tells you which it thinks it is looking
at. Detection is by filename and path only — never by sniffing content.

Override it when your filenames do not follow convention:

```bash
crewscore test --prompt-file ./odd-name.md --profile system_prompt
crewscore test --prompt-file ./odd-name.md --profile coding_agent_config
```

---

## Browser

[crewscore.ai](https://crewscore.ai) runs the same rules with no install. The
browser loads `score-engine.js`, generated from the Python engine by
`scripts/export_web_engine.py`; CI fails if the two drift apart.

Your prompt is scored in the page and never uploaded.
