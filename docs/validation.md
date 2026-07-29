# Validation: what the CrewScore number does and does not measure

**The score reports coverage of a published checklist. It does not rank prompt
quality, and it never has.** You do not have to take our word for either half —
both are derivable from the shipped rule catalog in about ten seconds.

This document reports what we can demonstrate, what we fixed after publishing
the arithmetic that showed it was broken, and what we tried to demonstrate and
then withdrew.

---

## Summary

| Question | Answer |
| --- | --- |
| Does a higher CrewScore mean a better prompt? | **No.** Not demonstrated. It means more of the checklist is written down. |
| Can a well-written prompt score well? | **Yes, since 0.3.0.** Covering all 23 controls scores 100. Before 0.3.0 the same prompt scored 28. |
| What does the number actually report? | **Coverage:** the share of the 23 published controls the text states. |
| Should you gate CI on the total? | **Prefer the findings** — which control is missing is more actionable than the average. |
| Are the configuration-smell detectors affected? | **No.** Separate feature, separate grounding ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)). |

---

## The defect we published, and then fixed

Through 0.1.0 each dimension scored
`min(100, round(15 + 85 x matched_rules / total_rules))`, where `total_rules`
counted **near-synonymous patterns for the same control**.

That formula did not ask *"is this control specified?"* It asked *"how many of
our phrasings did you happen to hit?"* Stating a control once, unambiguously,
matched about one pattern out of six and scored 24–32. **A prompt that stated
one control in each of the eight dimensions, clearly and once, scored
28/100 — below the lowest tier
boundary of 50.** Reaching 70 took the same control restated four to six
different ways, which is exactly the redundancy our own Context Bloat detector
flags as a defect.

So the tool rewarded, through its core formula, the precise anti-pattern it
reports as a smell — and the top two thirds of its scale were unreachable by
writing well. We published that arithmetic rather than the marketing.

**0.3.0 fixes it.** Rules are now grouped into the distinct **controls** they
express, and rules within a control are alternative phrasings rather than
additive evidence:

```
score = (100 * controls_covered + N // 2) // N     # N = controls in the dimension
```

Run `crewscore rules --concepts` to print the grouping. It is the denominator of
every dimension score, so it gets the same exposure as the regexes.

| Dimension | Rules | Controls | One control stated | All controls stated |
| --- | ---: | ---: | ---: | ---: |
| Injection defense | 10 | 3 | 33 | 100 |
| Hallucination policy | 8 | 4 | 25 | 100 |
| Citation discipline | 5 | 3 | 33 | 100 |
| Cost control | 5 | 2 | 50 | 100 |
| Human gate | 7 | 2 | 50 | 100 |
| Safe stop | 7 | 3 | 33 | 100 |
| Audit | 5 | 3 | 33 | 100 |
| Compliance | 9 | 3 | 33 | 100 |

Measured, old engine against new, on the same inputs:

| Prompt | 0.1.0 | 0.3.0 |
| --- | ---: | ---: |
| Bare assistant prompt | 0 | 0 |
| Partial hygiene | 20 | 29 |
| Hardened ops | 87 | 95 |
| States one control per dimension | 30 | 36 |
| **States all 23 controls** | **62** | **100** |

The floor is unchanged — a prompt with no guardrails still scores 0 — and the
ceiling is now reachable by writing each control down once.

### What this does *not* fix

**The number is still coverage, not quality.** A 100 means every control on the
checklist appears in the text. It does not mean the controls are well specified,
mutually consistent, or that the model will obey them — CrewScore reads text and
never runs the agent. Two further limits are unchanged:

- **Restating a control still cannot raise a score, by design.** That is the
  anti-bloat property, and it means the score is blind to how *thoroughly* a
  control is specified.
- **The controls are our judgement.** The grouping above is the most
  consequential call in the catalog. Disagree with one in an issue — that is
  why it is published as data rather than buried in the scorer.

Per-dimension provenance, including the three dimensions that ship known-weak,
is below and in `crewscore rules`.

---

## What we withdrew, and why

An earlier draft of this document reported a discrimination study: 283
production prompts against 1,085 GPT-Store prompts, with a length-matched
Cliff's delta, an AUC comparison against character count, and a table of
per-dimension recall.

**We audited our own study before publishing it and found arithmetic that does
not survive scrutiny.** Among the problems, all in the numbers as reported:

- A sensitivity paragraph claimed every alternative made the tool look *better*,
  then listed two effect sizes that were both **lower** than the baseline.
- A per-dimension rate was reported as "1 prompt in 283 (2.1%)". 1/283 is 0.35%.
  The hand-labelled sample was not 283 prompts, so the denominators in that
  table did not mean what the surrounding text said they meant.
- A recall of 60.0% was reported for a dimension present in 2 prompts. With
  n=2, the only achievable values are 0%, 50% and 100%.
- A reported total of matching lines was smaller than the minimum the study's
  own distributions require.
- The reported confidence interval and the reported p-value were mutually
  inconsistent, and no statistical test was named for any figure.
- The argument that the formula defect and the discrimination result were
  independent was wrong. The formula floors a large share of scores at exactly
  zero; those ties attenuate a rank statistic like Cliff's delta rather than
  leaving it untouched, so the two effects are confounded — and the error ran
  in the direction flattering to us.

Additionally, the document claimed the analysis was "reproducible from
`scripts/`". It was not: no such harness is committed to this repository.

We are not publishing numbers we cannot reproduce, in a document whose entire
purpose is rigor. The study was withdrawn pending a committed, executable
harness.

### That harness now exists

[`scripts/validate_corpus.py`](../scripts/validate_corpus.py) fetches both
corpora at pinned commit SHAs, scores them, runs the analysis, and **writes the
report itself** — [`docs/validation-corpus.md`](validation-corpus.md). Nothing
in that report is typed by hand, because hand-transcription is what produced
every error above. A test fails if the committed report does not match a fresh
run.

```
py scripts/validate_corpus.py
```

Each failure mode above is now an assertion that **fails the run and writes
nothing**: rates must be achievable at their own n, every rate carries its
denominator, the interval and the p-value come from resampling the same
statistic so they cannot contradict each other, and no 40-character run of
input text may appear in the output. The zero-floor confound is measured and
reported alongside a non-zero-only sensitivity run rather than asserted away.

**Result:** across 83 production agent prompts and 273 general-purpose
GPT-Store prompts, Cliff's delta = 0.672 (95% CI [0.549, 0.781], *p* = 0.0001,
two-sided permutation test). Coverage separates the two corpora. The numbers,
the test names, and the caveats are all in
[the generated report](validation-corpus.md).

Note what this does and does not change. This is *additional* evidence for a
conclusion the formula already establishes deterministically. The headline —
coverage, not quality — never depended on it, and a separation here means
production prompts **write more controls down**, not that they are better.

---

## Per-dimension caveats that still stand

These follow from the rule catalog, which ships with the package and which you
can inspect with `crewscore rules`:

- **Compliance** is keyword detection. It looks for regime names — HIPAA, GDPR,
  SOC 2. Naming a regulation is not implementing it, and the catalog grades this
  dimension `author-intuition` for exactly that reason.
- **Audit** and **Cost** hold five patterns each, aimed at language that is rare
  and highly variable in real prompts. **Read a `0` in these two as "the rules
  did not find it", not as "you failed to write it."**
- Every dimension is regex matching over text. None of it observes the agent.

`crewscore rules --json` gives you the full catalog with each rule's provenance
grade, so you can judge any individual rule yourself rather than trusting the
total.

---

## What is *not* affected

The **configuration-smell detectors** (Context Bloat, Init Fossilization, Lint
Leakage) are a separate feature replicating published work on a
2,000-repository corpus. They are advisory, never folded into any score, and
nothing here bears on them.

---

## Corrections

If you find an error in this document, please open an issue. The previous draft
was withdrawn because we audited it ourselves and it did not hold up; we would
rather be corrected than believed.

*Last updated for 0.1.0.*
