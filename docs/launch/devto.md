# Dev.to

## Title

```
Why your agent prompt is not a production plan (and a 30s structural check)
```

## Tags

`ai`, `agents`, `opensource`, `python`, `devops`

## Body

```markdown
# Why your agent prompt is not a production plan (and a 30s structural check)

You demoed an agent. It answered questions. Someone said “ship it.”

The system prompt still looks like:

> You are a helpful assistant that answers customer questions.

That is a persona, not a production plan.

## What production-shaped instructions usually include

Before runtime eval, red-teaming, or procurement theater, the **text** of the
instructions often needs signals like:

1. **Injection / override resistance** — reject “ignore previous instructions”
2. **Hallucination policy** — don’t fabricate; say when you don’t know
3. **Citations** — claims tied to sources when applicable
4. **Cost limits** — token/budget language so loops don’t print money
5. **Human gates** — approve before send / execute / publish
6. **Safe-stop** — halt when evidence is missing; escalate
7. **Audit** — log decisions / actions for review
8. **Compliance language** — PHI, GDPR, redaction, etc. when relevant

None of that proves the model will obey. It *does* catch the common case:
nobody wrote the hygiene down at all.

## CrewScore: offline structural scorecard

[CrewScore](https://crewscore.ai) is a small open-source CLI that scores those
signals on prompt text — offline, no API key:

```bash
pip install crewscore
crewscore test --prompt "You are a helpful assistant that answers customer questions."
```

You get eight dimension bars, an overall score, and a blunt tier
(e.g. **NOT PRODUCTION READY**).

Useful next steps:

```bash
# what’s missing?
crewscore test --prompt-file system.md --explain

# append guardrail patterns (review the diff!)
crewscore fix --prompt-file system.md

# CI gate
crewscore test --prompt-file system.md --threshold 50

# optional HTML report / badge / GitHub Action — see the README
```

Non-engineers evaluating vendors can use the same risk language via
`crewscore assess-vendor` or the checklist on [crewscore.ai](https://crewscore.ai).

## Anti-promise (please read this)

**CrewScore is structural hygiene on prompt text.**

| It is | It is not |
| --- | --- |
| Offline lint / scorecard for system prompts | Live adversarial red-teaming |
| A way to see missing guardrail *language* | Proof the model obeys at runtime |
| CI threshold + fix suggestions | Security or compliance certification |
| Vendor diligence checklist score | A SOC2 / legal opinion |

If you need attack suites, use tools built for that (e.g. garak, Promptfoo,
DeepEval). CrewScore sits **before** that stack: make the instructions
honest, then stress-test behavior.

Structural score ≠ red-team. Structural score ≠ certified production-safe.

## Why bother?

Viral OSS CLIs work when one command produces a number people can share —
and when the product refuses to lie about what that number means.

Score a prompt. Complain about the score. Fix a gap. Gate the PR.

```bash
pip install crewscore
```

- Site: https://crewscore.ai  
- Repo: https://github.com/shmindmaster/crewscore  

If a dimension is wrong for your domain, open an issue — the trust moat is
honesty, not a bigger claim.
```
