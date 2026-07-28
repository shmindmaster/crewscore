# Show HN

## Title

```
Show HN: CrewScore – offline production-hygiene scorecard for AI agent prompts
```

## Submission URL

https://github.com/shmindmaster/crewscore  
(or https://crewscore.ai if the demo is the better first click)

## Body (optional text field)

```
CrewScore is a small offline CLI that structurally scores AI agent system prompts
for production-hygiene signals — injection language, hallucination policy,
citations, cost limits, human gates, safe-stop, audit, compliance — then can
append missing guardrail patterns and fail CI when the score drops.

  pip install crewscore
  crewscore test --prompt "You are a helpful assistant..."

No API key. No model calls. Pattern match on the prompt text, not a live attack suite.

What it is not: red-teaming, runtime enforcement, or a safety certification.
Structural score ≠ proof the model will obey the text.

Demo: https://crewscore.ai
Repo:  https://github.com/shmindmaster/crewscore
```

## First comment (post immediately)

```
Author here — a few honest notes so expectations stay clear.

How scoring works
- Offline structural scan of system-prompt *text* (regex / pattern style signals).
- Eight dimensions → overall 0–100 and a tier (e.g. NOT PRODUCTION READY).
- `crewscore test --explain` shows which patterns matched or are missing.
- `crewscore fix` can append guardrail sections so you see a before/after delta.
- Optional HTML report, SVG badge, and a GitHub Action for threshold gates.
- Non-engineers: `crewscore assess-vendor` (and the web demo) is a 10-question
  diligence checklist with the same risk language — not a SOC2 opinion.

What this is not
- Not live adversarial red-teaming (use garak / Promptfoo / etc. for that).
- Not runtime tool-gating or proof the model will obey the prompt.
- Not a security or compliance certification.

Why ship it anyway
Most “agent is ready” claims skip a basic hygiene pass on the instructions
themselves. CrewScore is the 30-second smoke test and CI lint layer before
heavier eval stacks.

Install:
  pip install crewscore
  crewscore test --prompt "You are a helpful assistant that answers questions."

Site: https://crewscore.ai
Happy to answer questions / roast bad claims in the README.
```
