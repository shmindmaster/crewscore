# Validation: what the CrewScore number does and does not measure

**The score cannot rank prompt quality, and you do not have to take our word
for it — you can prove it from the shipped rule catalog in about ten seconds.**

This document reports what we can demonstrate, and is explicit about what we
tried to demonstrate and then withdrew.

---

## Summary

| Question | Answer |
| --- | --- |
| Does a higher CrewScore mean a better prompt? | **No.** Not demonstrated, and the formula argues against it. |
| Can a well-written prompt score well? | **No.** Stating all eight controls clearly, once each, scores **28/100** — below the lowest tier. |
| What does the number actually report? | **Coverage:** which controls the text mentions, and how many different ways. |
| Should you gate CI on the total? | **No.** Gate on the findings — which rule fired, which did not. |
| Are the configuration-smell detectors affected? | **No.** Separate feature, separate grounding ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)). |

---

## The proof: a perfect prompt fails

Each dimension scores `min(100, round(15 + 85 x matches / total_rules))`, where
`total_rules` is the number of near-synonymous patterns that dimension holds.

A dimension therefore does not ask *"is this control specified?"* It asks
*"how many of our phrasings did you happen to hit?"* Stating a control once,
unambiguously, matches roughly one pattern.

Run this against the installed package:

```python
from crewscore.scoring import DIMENSION_KEYS, overall_score
from crewscore.scorers.structural_analysis import SCORER_MAP

def dim(matches, total):
    return 0 if not total or not matches else min(100, round(15 + 85 * matches / total))

per = {k: dim(1, len(SCORER_MAP[k])) for k in DIMENSION_KEYS}
print(per, overall_score(per))
```

| Dimension | Rules | Score for stating it once | Restatements needed to reach 70 |
| --- | ---: | ---: | ---: |
| Injection defense | 8 | 26 | 6 |
| Hallucination policy | 8 | 26 | 6 |
| Citation discipline | 5 | 32 | 4 |
| Cost control | 5 | 32 | 4 |
| Human gate | 6 | 29 | 4 |
| Safe stop | 7 | 27 | 5 |
| Audit | 5 | 32 | 4 |
| Compliance | 9 | 24 | 6 |

**A prompt that states all eight controls clearly, once each, scores 28/100.**
Stating every one of them *twice* still only reaches **41/100**. The lowest tier
boundary is 50. The top of the scale is unreachable by clear writing — it is
reachable only by saying the same thing four to six different ways, which is
exactly the redundancy our own Context Bloat detector flags as a defect.

That is a scoring bug, and it is sufficient on its own to establish the point of
this document: **the number is coverage, not quality.** A high score means the
text is verbose about a control. A low score means a control may be missing —
which is genuinely useful, and is the job the tool should be trusted with.

This defect is deliberately **not** fixed in 0.1.0. Repairing the formula
changes every score, and belongs in a release that changes scoring on purpose,
alongside the rule-precision work.

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
purpose is rigor. **The corpus study is withdrawn pending a committed,
executable harness.** When it returns it will ship as code in this repository,
runnable by anyone against corpora they clone themselves, with the test named
and the denominators stated.

Note what this does and does not change. The withdrawn study was *additional*
evidence for a conclusion the formula already establishes deterministically. The
headline — coverage, not quality — does not depend on it.

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
