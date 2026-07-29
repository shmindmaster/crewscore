# After CrewScore — live eval handoff

CrewScore is a **structural pre-gate**: offline pattern scan of agent instruction
text. It is intentionally *not* a red-team, pen test, or runtime proof.

After selecting the written controls your product needs and protecting them from
regression, graduate to live testing.

## One command handoff

```bash
crewscore export-eval --prompt-file ./agents/system-prompt.md -o ./crewscore-eval
```

This **does not run** Promptfoo or garak. It:

1. Scores the prompt offline with the published ruleset
2. Writes `promptfooconfig.yaml` with starter cases **biased toward missing
   written controls**
3. Writes `README-EVAL.md` with suggested garak probes for those gaps
4. Writes `crewscore-eval-manifest.json` (prompt-free: control IDs and scores only)

Optional:

```bash
crewscore export-eval --prompt-file ./prompt.md -o ./crewscore-eval --provider openai:gpt-4o
```

## What CrewScore already covered

- Presence of injection / override language in the prompt
- Hallucination, citation, cost, HITL, safe-stop, audit, compliance *wording*
- CI gate so those signals do not regress silently
- Optional `fix` templates (text only — pair with real runtime controls)

## What it did **not** cover

| Gap | Why it matters |
|-----|----------------|
| Live jailbreak / injection resistance | Models may ignore prompt text under attack |
| Multi-turn agent tool abuse | Needs a running agent and attack scenarios |
| App-specific correctness | Domain evals, golden sets, regression suites |
| Vendor runtime security | SOC2/pen-test evidence, not a self-attest form |

## Recommended next tools

### [Promptfoo](https://www.promptfoo.dev/)

Use when you want **YAML-defined evals**, assertions, and CI on real model responses.

Typical path:

1. `crewscore export-eval --prompt-file ...` (or copy your system prompt by hand)
2. Edit the generated provider and product-specific assertions
3. Fail CI on assertion regressions — separate from CrewScore’s structural gate

```bash
npx promptfoo@latest eval -c crewscore-eval/promptfooconfig.yaml
```

### [garak](https://github.com/NVIDIA/garak) (NVIDIA)

Use when you want a **known-attack vulnerability scanner** against a live model endpoint.

Typical path:

1. Read suggested probes from `README-EVAL.md` / the manifest
2. Point garak at your model / agent API
3. Treat findings as security work, not prompt-lint debt

### Other options

- **PyRIT**, **DeepEval**, custom harnesses — when you need agent-specific multi-step attacks or quality metrics.

## Suggested pipeline

```text
edit agent instructions
        │
        ▼
 crewscore scan . --require human_gate.approval_required,safe_stop.stop_condition
                                      # protect selected written controls
        │
        ▼
 crewscore export-eval --prompt-file ./agents/system-prompt.md
                                      # structural gaps -> starter live configs
        │
        ▼
 promptfoo eval / red-team           # live response assertions
        │
        ▼
 garak (or similar)                  # known-attack scan on the endpoint
```

Keep CrewScore in CI even after you add live tools: it is cheap, offline, and catches “we deleted the HITL paragraph” before expensive evals run.

## Honesty reminder

- A high CrewScore does **not** mean “safe in production.”
- `crewscore fix` templates can **inflate** the structural number without changing runtime behavior.
- Generated Promptfoo/garak suggestions are **starters**, not a complete security program.
- Live tools can still miss novel attacks; defense in depth remains on you.

See the [Scoring charter](scoring.md#charter) and [CLI reference](cli.md).
