# Validation: what the CrewScore number does and does not measure

We tested our own scorer against 1,368 real system prompts. **It failed to
distinguish production prompts from amateur ones.** This document reports that
result, because you should know it before you use the number for anything.

Everything below is reproducible from `scripts/` against public corpora. No
prompt text is redistributed here — only aggregate statistics.

---

## Summary

| Question | Answer |
| --- | --- |
| Does a higher CrewScore mean a better prompt? | **No. Not demonstrated.** |
| Does it separate production prompts from amateur ones? | **No**, once length is controlled (delta +0.061, p=0.36) |
| Is there anything simpler that separates them better? | **Yes — `wc -c`.** Character count alone scores AUC 0.863 vs CrewScore's 0.800 |
| Is the number useful at all? | **Yes, as coverage:** it tells you which governance controls you have not written down |
| Are the configuration-smell detectors affected? | **No.** They are a separate, independently-grounded feature ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)) |

---

## The discrimination test

If the eight governance dimensions measure prompt maturity, prompts written by
teams shipping to millions of users should score meaningfully above prompts
written by hobbyists. That is a falsifiable claim, so we tested it.

**Arm A — production prompts** (n=283): system prompts extracted from shipped
commercial AI products, drawn from public leaked-prompt collections.

**Arm B — amateur prompts** (n=1,085): GPT-Store custom-GPT instructions, drawn
from a public collection.

| | Arm A (production) | Arm B (amateur) |
| --- | ---: | ---: |
| n | 283 | 1,085 |
| Median score | **7 / 100** | **0 / 100** |
| IQR | 3 – 15 | 0 – 3 |
| Max | 50 | 16 |

Raw Cliff's delta is **+0.601** — which looks like a strong result, and is not
one. Production prompts are much longer than amateur prompts, and the scorer
rewards length indirectly: more text means more chances for a regex to fire.

Matching on length (caliper-matched pairs, n=130) removes the effect:

| Measure | Value |
| --- | --- |
| **Length-matched Cliff's delta** | **+0.061** |
| 95% CI | **−0.050 to +0.172** (crosses zero) |
| p | **0.36** |

The confidence interval includes zero. At equal length, we cannot show that
production prompts score higher than amateur ones.

**And a one-line baseline beats us.** Discriminating the two arms by character
count alone gives AUC **0.863**. The full eight-dimension CrewScore gives AUC
**0.800**. `wc -c` is the better classifier.

### The curation was checked against us, not for us

Every judgment call in building the corpora was sensitivity-tested, and each
alternative made the tool look *better*, not worse — so the headline result is
the conservative one. Folding tool schemas back into prompt text raises raw delta
to +0.590; including auxiliary skill documents gives +0.503. We report the
length-matched figure regardless, because length matching is the correction that
matters.

### Also true, and damning on its own

- **99.3%** of production prompts (281 of 283) land in the worst tier.
- The **highest score across all 1,368 real files is 50/100.** The top half of
  the scale is empty. Nothing real reaches it.

---

## Why the scale is empty: the aggregation formula

Each dimension scores `min(100, round(15 + 85 x matches / total_rules))`.

Because a dimension holds several near-synonymous patterns, a control that is
stated **once, clearly** matches one pattern and scores **24–32** (median 32
across 89 correctly-detected cells). To score high you must restate the same rule
five or six different ways.

That is backwards. It rewards exactly the redundancy our own Context Bloat
detector flags, and it is why no real prompt clears 50.

This is a defect in the formula, independent of the regexes, tracked for the next
release. Note carefully what it does and does not explain: it explains why
*absolute* scores are low, but **not** the discrimination failure — Cliff's delta
is rank-based and unaffected by a monotone compression of the scale.

## Why discrimination fails: precision

Across the corpus, 103 of 22,578 lines match any rule, and **about 84% of those
matches are false positives** — text that fires a pattern without stating the
control. Roughly half of all rule firings are not on-target.

Restricting to genuine matches, the correlation between score and length falls
from r=+0.465 to **r=+0.034**. The length relationship is an artifact of
imprecise patterns, not a deliberate length term. (There is no length term; one
existed in 0.2.x and was removed during 0.3.x development, which never
shipped; 0.4.0 is the first public release without it.)

We measured length normalization as a fix and **rejected it**: it made the
correlation worse (+0.253), and it would double-charge for length, which is
already priced separately as Context Bloat.

---

## Per-dimension construct validity

Not all eight dimensions fail the same way. We hand-labelled a sample of
production prompts for whether each control is genuinely present, then measured
whether the rules find it.

| Dimension | Control actually present | Recall when present | Status in 0.4.0 |
| --- | ---: | ---: | --- |
| Hallucination policy | 62.5% | 53.3% | Repair planned |
| Safe stop | 60.4% | 79.3% | Precision work planned |
| Citation discipline | 43.8% | 76.2% | Precision work planned |
| Human gate | 39.6% | **36.8%** | Repair planned — largest recoverable recall |
| Cost control | 37.5% | 50.0%, but **0% on-target** | **Low validity** — re-specification planned |
| Compliance | 4.2% name a regime | 60.0% | **Low validity** — re-specification planned |
| Injection defense | 29.2% | 57.1% | Precision work planned |
| Audit | **2.1%** (1 prompt in 283) | n=1, not estimable | **Low validity** — removal under consideration |

Three dimensions — **Cost, Compliance, and Audit** — are shipping with known-poor
validity. We are disclosing rather than quietly removing them, because removing
dimensions changes every score and that belongs in a release that changes scoring
on purpose, with the regex work done alongside it.

**Read `audit` and `cost` results with suspicion.** A 0 there mostly means the
rules did not find something, not that you failed to write it.

---

## So what is the number for?

**It is coverage, not quality.**

A low score is actionable and usually correct in direction: you probably have not
written down an explicit injection policy, human gate, or safe-stop rule. Writing
those down is worth doing.

A high score means the text is present. It does not mean the agent will obey it,
that the prompt is good, or that it is better than a prompt scoring lower. We
have no evidence for any of those, and the study above is evidence against the
last one.

**Do not** rank prompts, teams, or vendors by this number. **Do not** treat a
threshold as a safety bar. Use the findings — which rule fired, which did not —
rather than the total.

---

## What is *not* affected

The **configuration-smell detectors** (Context Bloat, Init Fossilization, Lint
Leakage) are a separate feature with separate grounding, replicating published
work on a 2,000-repository corpus. They are advisory, never folded into any
score, and nothing in this study bears on them.

---

## Reproducing this

The analysis harness lives in `scripts/`. Corpora are public GitHub collections
of leaked system prompts and GPT-Store instructions, cloned at pinned commits.

We deliberately do **not** redistribute prompt text. Those collections carry a
CC0 license on the maintainer's *compilation*, which is not a grant from the
vendors over the underlying prompt text. Clone them yourself and point the
harness at your clone; only aggregate statistics belong in a report.

---

*Last updated for 0.4.0. If you find an error in this analysis, please open an
issue — we would rather be corrected than believed.*
