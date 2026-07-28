---
name: Scoring false positive/negative
about: Pattern matched wrong or missed a real guardrail
title: "[scoring] "
labels: scoring
---

> **Check [`docs/validation.md`](../../docs/validation.md) first.** Some of this
> is measured and already known — roughly 84% of rule matches across our corpus
> are false positives, and `cost`, `compliance`, and `audit` ship with
> known-poor construct validity. A report on those three confirms what we
> already published; a **concrete pattern that would fix it** is what we need.
> Precision reports on the other five dimensions are very welcome.

## Dimension

injection / hallucination / citation / cost / human_gate / safe_stop / audit / compliance

## Prompt excerpt (redact secrets)

```
```

## What CrewScore did

- Score:
- Matched / missing (from `--explain` if possible):

## What you expected

## Suggested pattern (optional)
