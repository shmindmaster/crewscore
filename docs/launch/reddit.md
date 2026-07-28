# Reddit

Utility first. No hype. Include the anti-promise in every post.  
Do not spam all three subs at once if a sub’s rules discourage cross-posting — stagger and tailor.

---

## r/LocalLLaMA

**Title**

```
CrewScore – offline CLI that structurally scores agent system prompts (no API key)
```

**Body**

```
I open-sourced a small tool that does a structural production-hygiene scan on
AI agent system prompts — injection language, hallucination policy, citations,
cost limits, human gates, safe-stop, audit, compliance signals — then can
append missing guardrail patterns and gate CI on a threshold.

  pip install crewscore
  crewscore test --prompt "You are a helpful assistant..."

No model calls. Offline. Optional --explain, HTML report, badge, GitHub Action.
There’s also a non-tech vendor checklist mode if you evaluate tools.

Honest limits: this is pattern matching on prompt *text*. It is not live
red-teaming, not runtime enforcement, and not a safety certification.
Structural score ≠ proof the model will obey the instructions.

Repo: https://github.com/shmindmaster/crewscore
Site: https://crewscore.ai

Happy to take “your dimension X is wrong” feedback.
```

---

## r/MachineLearning

**Title**

```
[P] CrewScore: structural scorecard for agent system-prompt production hygiene
```

**Body**

```
Project: CrewScore — offline structural scorecard for AI agent system prompts.

Motivation: teams ship agents after a demo without a systematic pass over the
instruction text (injection resistance language, “don’t fabricate,” human
gates on side effects, cost/audit/compliance signals, etc.). Heavier stacks
(Promptfoo, garak, DeepEval) own live eval; this is the cheap lint/scorecard
layer before that.

  pip install crewscore
  crewscore test --prompt-file system.md --explain
  crewscore fix --prompt-file system.md
  # optional CI threshold + HTML report + GitHub Action

What it measures: structural signals in the prompt text → 8 dimensions + overall.
What it does not measure: runtime obedience, tool-call policy enforcement, or
adversarial robustness under live attack.

Not a certification. Structural ≠ red-team.

https://crewscore.ai
https://github.com/shmindmaster/crewscore
```

---

## r/ChatGPTCoding

**Title**

```
30-second structural check for your agent system prompt (CrewScore, offline CLI)
```

**Body**

```
If you maintain a system prompt for an agent / GPT / custom GPT workflow:

  pip install crewscore
  crewscore test --prompt "paste your system prompt"

You get a scorecard (8 dimensions + overall). Low scores usually mean missing
guardrail language. `crewscore fix` can append patterns; CI can fail if the
score drops.

Site demo: https://crewscore.ai

Important: this only looks at the *text* of the prompt. It is not a red-team,
not runtime safety, and not a certification. Use it as hygiene / lint before
heavier testing.

Repo: https://github.com/shmindmaster/crewscore
```
