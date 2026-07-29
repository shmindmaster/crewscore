# After CrewScore — live eval handoff

CrewScore is a **structural pre-gate**: offline pattern scan of agent instruction text. It is intentionally *not* a red-team, pen test, or runtime proof.

After selecting the written controls your product needs and protecting them from
regression, graduate to live testing.

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

1. Export or copy your system prompt into a Promptfoo config.
2. Add red-team / custom prompts that matter for your product.
3. Fail CI on assertion regressions — separate from CrewScore’s structural gate.

### [garak](https://github.com/NVIDIA/garak) (NVIDIA)

Use when you want a **known-attack vulnerability scanner** against a live model endpoint.

Typical path:

1. Point garak at your model / agent API.
2. Run injection / jailbreak / leakage probes.
3. Treat findings as security work, not prompt-lint debt.

### Other options

- **PyRIT**, **DeepEval**, custom harnesses — when you need agent-specific multi-step attacks or quality metrics.

## Suggested pipeline

```text
edit agent instructions
        │
        ▼
 crewscore scan . --require human_gate.approval_required,safe_stop.stop_condition
                                      # example: protect selected written controls
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
- Live tools can still miss novel attacks; defense in depth remains on you.

See the [Scoring charter](../README.md#scoring-charter) in the README.
