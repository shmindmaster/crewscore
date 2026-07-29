# Scoring governance

CrewScore's published score is a deterministic count of written public
controls. It is not a maturity model, certification, runtime test, or
benchmark. Changes to rules, control grouping, or score arithmetic therefore
need more than a code review.

## Maintainer policy

1. Propose the change with the affected rule IDs, controls, examples, and
   expected score delta.
2. State provenance in `DIMENSION_PROVENANCE`: evidence-backed, plausible, or
   author-intuition. Evidence-backed claims name their citation.
3. Add a regression test and regenerate `score-engine.js` when the browser
   payload changes.
4. Re-run the reproducible validation corpus and update generated artifacts,
   methodology, package/ruleset version, and CHANGELOG in the same pull
   request.
5. Do not fold configuration smells, prompt length, recency, or template
   quantity into the published score without new evidence and an explicitly
   documented scoring change.

## Community input

False positives and false negatives are welcome when they include a minimal
synthetic or safely redactable example, the expected control, actual finding,
and CrewScore/ruleset version. They are evidence for a future change, not an
automatic change to a safety rule.

## Releases

Scoring changes receive a ruleset/version update and a CHANGELOG entry. Product
or documentation changes must not silently imply a different score meaning.
The validation record explicitly distinguishes the reproducible 356-prompt
snapshot from the withdrawn 1,368-prompt study.
