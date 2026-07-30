# Scoring and controls

**One engine.** The Python CLI and [crewscore.ai](https://crewscore.ai) use the
same patterns. The browser loads `score-engine.js`, generated from Python by
`scripts/export_web_engine.py`; CI fails if the two drift apart.

This page is the canonical product description of the formula, dimensions,
charter, and maintainer rules for changing them.

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
| Audit Trail | Log decisions, tamper-evident trail language | plausible |
| Compliance Readiness | HIPAA / SOC 2 / GDPR / EU AI Act handling language | author-intuition |

Grades are per dimension, not per rule. Full rationale and citations:
`crewscore rules`.

**Read `audit`, `cost`, and `compliance` results with suspicion.** A `0` there
means the rules did not find something, not that you failed to write it.
Compliance in particular is keyword detection: naming a regulation is not
complying with it.

List every control ID:

```bash
crewscore rules --concepts
crewscore rules --json
```

---

## Score tiers

| Score | Verdict |
|-------|---------|
| 90–100 | `STRUCTURAL: STRONG` |
| 70–89 | `STRUCTURAL: OK WITH GAPS` |
| 50–69 | `STRUCTURAL: WEAK` |
| 0–49 | `STRUCTURAL: CRITICAL GAPS` |

Labels describe **prompt-text coverage**, not production certification.
Prefer explicit control policies over treating these tiers as a safety bar.

---

## Two artifacts, two rulesets

| Artifact | Examples | Judged on |
|----------|----------|-----------|
| **Coding-agent config** | `AGENTS.md`, `CLAUDE.md`, `.cursorrules` | Configuration smells |
| **Agent system prompt** | `system-prompt.md`, paths under `prompts/` / `agents/` | The 8 governance dimensions |

Classification is filename/path only (`profiles.classify_path`). Config JSON
omits `overall` / `dimensions` / `findings` entirely — see
[architecture](architecture.md). Smells never change the score.

---

## Charter

1. CrewScore measures **coverage: presence of hygiene signals in text**. Not
   agent behaviour, not prompt quality.
2. **A low score is actionable.** **A high score means the text is present.**
   Do not rank prompts, teams, or vendors by this number.
3. **Prefer the findings to the total.**
4. **Every rule is public**, versioned by ruleset, and deterministic —
   `crewscore rules --json`.
5. **Every dimension declares provenance** (`evidence-backed`, `plausible`, or
   `author-intuition`).
6. **Length is never a score.** Length may appear as a configuration smell.
7. `fix` improves **text coverage**, not runtime safety.
8. Never call a score a **certification**, **audit**, or **red-team result**.
9. When in doubt, **under-score** rather than inflate.
10. **Publish arithmetic that makes us look bad** when we discover scale bugs —
    see [validation.md](validation.md).

Source of truth:
[`crewscore/scorers/structural_analysis.py`](../crewscore/scorers/structural_analysis.py).

---

## Scoring governance (how rules change)

The published score is a deterministic count of written public controls. It is
not a maturity model, certification, runtime test, or benchmark. Changes to
rules, control grouping, or score arithmetic need more than a casual code review.

### Maintainer policy

1. Propose the change with affected rule IDs, controls, examples, and expected
   score delta.
2. State provenance in `DIMENSION_PROVENANCE`: evidence-backed, plausible, or
   author-intuition. Evidence-backed claims name their citation.
3. Add a regression test and regenerate `score-engine.js` when the browser
   payload changes (`python scripts/export_web_engine.py`).
4. Re-run the reproducible validation corpus and update generated artifacts,
   methodology, package/ruleset version, and CHANGELOG in the same PR when the
   score meaning changes.
5. Do not fold configuration smells, prompt length, recency, or template
   quantity into the published score without new evidence and an explicitly
   documented scoring change.

### Community input

False positives and false negatives are welcome when they include a minimal
synthetic or safely redactable example, the expected control, actual finding,
and CrewScore/ruleset version. They are evidence for a future change, not an
automatic change to a safety rule. Use the issue templates under
`.github/ISSUE_TEMPLATE/`.

### Releases

Scoring changes receive a ruleset/version update and a CHANGELOG entry. Product
or documentation changes must not silently imply a different score meaning.
The validation record distinguishes the reproducible 356-prompt snapshot from
the withdrawn 1,368-prompt study.

---

## Further reading

- [What the number does and does not measure](validation.md)
- [Corpus validation](validation-corpus.md) — `scripts/validate_corpus.py`
- [When to graduate to live eval tools](next-steps-eval.md)
- [Control policies and SARIF](policies.md)
- [Architecture](architecture.md)
