---
name: Scoring false positive/negative
about: Pattern matched wrong or missed a real guardrail
title: "[scoring] "
labels: scoring
---

> **Check [`docs/validation.md`](../../docs/validation.md) first.** Some of this
> is already known and disclosed. In particular, `cost`, `compliance`, and
> `audit` ship with known-poor construct validity: `cost` and `audit` hold only
> five patterns each, and `compliance` is keyword detection over regime names,
> graded `author-intuition` in the catalog. A report on those three confirms
> what we already published; a **concrete pattern that would fix it** is what we
> need. Precision reports on the other five dimensions are very welcome.
>
> Note also that the total is coverage, not quality — stating all eight controls
> clearly, once each, scores 28/100 — so "my good prompt scored low" is expected
> behavior, not a false negative. Report the specific rule that should have
> matched instead.

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
