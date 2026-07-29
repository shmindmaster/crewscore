# How scoring works

**One engine.** The Python CLI and [crewscore.ai](https://crewscore.ai) use the
same patterns. The browser loads `score-engine.js`, generated from Python by
`scripts/export_web_engine.py`; CI fails if the two drift apart.

---

## The formula, in full

Each of the eight dimensions is a small set of distinct **controls** — 23 in
total. A dimension scores on how many of its controls your prompt states:

```
dimension_score = (100 × controls_covered + N ÷ 2) ÷ N     # N = controls in the dimension
overall         = floor(mean of the 8 dimension scores)
```

A control is covered when **any one** of its rules matches. Rules within a
control are alternative phrasings, not additive evidence, so restating the same
rule five ways scores it once.

There is no length term and no floor. `crewscore rules --concepts` prints the
grouping — it is the denominator, so it is published as data.

| What the prompt does | What it scores |
| --- | --- |
| Nothing written down | **0** |
| One control in each dimension | **36** |
| All 23 controls | **100** |
| One control restated five ways | same as stating it once |

Integer arithmetic, rounded half up — Python's `round()` is half-to-even and
JavaScript's `Math.round` is half-up, and the two engines must never disagree
about the same prompt.

---

## The eight dimensions

| Dimension | What the scanner looks for | Provenance |
|-----------|----------------------------|------------|
| Prompt Injection Resistance | Reject-override, do-not-reveal-system, jailbreak language | evidence-backed |
| Safe-Stop Behavior | Halt when evidence is missing or uncertain | evidence-backed |
| Cost Runaway Protection | Token, budget, max-length limits | evidence-backed |
| Hallucination Guardrails | No fabrication, "I don't know", grounded-only claims | plausible |
| Source Citation | Claims must cite sources or evidence | plausible |
| Human-in-the-Loop Gates | Approval before send, write, or publish | plausible |
| Audit Trail | Log decisions, immutable-trail language | plausible |
| Compliance Readiness | HIPAA / SOC 2 / GDPR / EU AI Act handling language | author-intuition |

Grades are per dimension, not per rule — the rules inside a dimension share one
justification, and per-regex citations would be false precision. Full rationale
and citations: `crewscore rules`.

**Read `audit`, `cost` and `compliance` results with suspicion.** A `0` there
means the rules did not find something, not that you failed to write it.
Compliance in particular is keyword detection: naming a regulation is not
complying with it.

---

## Score tiers

| Score | Verdict |
|-------|---------|
| 90–100 | `STRUCTURAL: STRONG` |
| 70–89 | `STRUCTURAL: OK WITH GAPS` |
| 50–69 | `STRUCTURAL: WEAK` |
| 0–49 | `STRUCTURAL: CRITICAL GAPS` |

Labels describe **prompt-text coverage**, not production certification.
They rank coverage, nothing else. Set
thresholds against what your files actually score, not against this ladder.

---

## Charter

Principles we ship by, in order of how much they constrain us:

1. CrewScore measures **coverage: presence of hygiene signals in text**. Not
   agent behaviour, not prompt quality.
2. **A low score is actionable** — you probably have not written down an
   explicit injection policy, human gate, or safe-stop rule, and writing those
   down is worth doing. **A high score means the text is present.** It does not
   mean the agent will obey it, or that this prompt beats one scoring lower.
   Do not rank prompts, teams, or vendors by this number.
3. **Prefer the findings to the total.** Which control is missing is the part
   we can defend.
4. **Every rule is public**, versioned by ruleset, and deterministic — no LLM,
   no hidden model. `crewscore rules --json`.
5. **Every dimension declares where it came from**, graded `evidence-backed`,
   `plausible`, or `author-intuition`, with citations — including the one that
   is explicitly author-intuition.
6. **Length is never a score.** Long files cost tokens on every run, which is a
   defect rather than a virtue. Length is reported as a
   [configuration smell](../README.md#configuration-smells), never as points.
7. `fix` improves **text coverage**, not runtime safety. It reports its own
   context cost, and flags its own output as boilerplate when that output
   dominates a file.
8. We never call a score a **certification**, **audit**, or **red-team result**.
9. When in doubt, **under-score** rather than inflate.
10. **We publish the arithmetic that makes us look bad.** Through `0.1.0` the
    formula divided by rule count, so a well-written prompt could not exceed
    the lowest tier. We published that before fixing it — see
    [validation.md](validation.md).

Source of truth:
[`crewscore/scorers/structural_analysis.py`](../crewscore/scorers/structural_analysis.py).

---

## Further reading

- [What the number does and does not measure](validation.md) — with the
  arithmetic, the per-dimension caveats, and the study we withdrew.
- [Corpus validation](validation-corpus.md) — generated by
  `scripts/validate_corpus.py` against 356 real prompts.
- [When to graduate to live eval tools](next-steps-eval.md).
