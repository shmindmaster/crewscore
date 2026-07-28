# Changelog

All notable changes to CrewScore are documented here.

This project follows [Semantic Versioning](https://semver.org/). The `--json`
payload shape, the CLI exit codes, and the GitHub Action's outputs are treated
as the public contract; breaking changes to any of them get a minor bump
pre-1.0 and are listed under **Breaking** below.

---

## [0.4.0] — 2026-07-28

The honest reframe. CrewScore measures **coverage**, not quality — and that is
provable from the shipped rule catalog, without any corpus: a prompt that states
all eight governance controls clearly, once each, scores **28/100**, below the
lowest tier. This release publishes that rather than the marketing.

### Added

- **`docs/validation.md` — what the number does and does not measure.** Its
  central proof is deterministic and reproducible against the installed package:
  each dimension scores `min(100, round(15 + 85 × matches / total_rules))`, so a
  control stated once and clearly scores **24–32**, all eight stated once each
  average **28/100**, and stating every one of them twice still reaches only
  **41/100**. Reaching 70 requires restating the same control four to six
  different ways — the exact redundancy the Context Bloat detector flags. A
  metric a well-written prompt cannot pass is coverage, not quality. The document
  also carries the per-dimension caveats that follow from the catalog — including
  the three dimensions (`cost`, `compliance`, `audit`) now shipping with
  **known-poor validity, disclosed rather than quietly dropped** — and records a
  corpus study that was **withdrawn** before publication after our own audit
  found arithmetic in it that did not survive scrutiny. Those figures are not
  cited anywhere, not even as preliminary; the coverage-not-quality conclusion
  never depended on them.
- **Artifact profiles.** Coding-agent config (`AGENTS.md`, `CLAUDE.md`,
  `.cursorrules`) is now classified as `CODING_AGENT_CONFIG` and judged on
  configuration smells instead of being handed a governance grade it was never
  designed to earn. Classification is by filename/path only — content sniffing
  is deliberately not done.
- **Configuration-smell detectors** (Context Bloat, Init Fossilization, Lint
  Leakage), replicating published work on a 2,000-repository corpus
  ([arXiv:2606.15828](https://arxiv.org/abs/2606.15828)). Advisory only — never
  folded into any score.
- **`--max-smells`** gate, on the CLI and as an Action input. This is the gate
  that applies to coding-agent config, where `--threshold` does not.
- **`--profile`** override on `scan`, so the advice the tool prints is
  actionable rather than decorative.
- **`scored` output on the GitHub Action.** An empty `score` cannot guard
  itself — GitHub casts `''` to `0` in numeric comparisons, so
  `if: outputs.score < 50` was true for a run that measured nothing. Guard on
  `steps.<id>.outputs.scored == 'true'`.
- **Rule provenance** in the catalog: every rule declares where it came from.

### Changed

- **Ruleset is now `crewscore-hygiene@0.4.0`.** No `0.3.x` was ever published
  (the last public release is `0.2.7`), so no
  comparison history is invalidated by the renumber.
- Package description, README, `AGENTS.md`, and the GitHub Action manifest no
  longer claim "production-readiness". The number is coverage of controls you
  wrote down. It does not predict whether an agent obeys them.
- Scan and summary output surfaces branch on `governance_applicable` everywhere:
  no headline score, tier, badge, or verdict is emitted for coding-agent config.

### Breaking

- **`--json` payload shape for coding-agent config.** Config rows no longer
  carry `overall`, `dimensions`, `findings`, or `transparency` — not as zero,
  not as an empty value, the keys are absent. Consumers that read `r['overall']`
  off every row will `KeyError`. Branch on `governance_applicable` first; treat
  it as `True` when missing, which is correct for payloads written before
  profiles existed.
- **`crewscore fix` exit codes and refusal behavior.** `fix` now declines to
  inject governance templates into coding-agent config rather than writing
  guardrail prose into an `AGENTS.md`. A forced write is recorded in the JSON
  payload as `forced_governance_write: true`, carried on `--plan` and
  no-changes payloads too.

### Fixed

- **Script-injection exposure in `action.yml`**: user-controlled inputs were
  interpolated directly into the `run:` shell body. They now arrive via `env:`.
  This was verified live — a crafted `threshold` value executed a command
  against the unfixed manifest.
- **Scoring no longer rewards context bloat.** The length bonus present in 0.2.x
  is gone; measured false-positive rules were removed.
- `_git_commit_count` returned a wrong smell verdict on shallow clones
  (`--depth 1`); it now returns `None` and the detector abstains.
- `setup.cfg` / `tox.ini` are only treated as linter config when they actually
  carry the relevant sections.
- The Python and JS engines are verified in lockstep by a check that no longer
  compares a file against itself.
- The CI self-test no longer reads a governance score off config rows.
- `--threshold` on a config-only scan now says it is a no-op instead of silently
  passing.

### Known limitations

Read `docs/validation.md` before using the score for anything. In short: do not
rank prompts, teams, or vendors by this number, and do not treat a threshold as
a safety bar. Use the per-rule findings — which rule fired, which did not.

The aggregation formula (a control stated once clearly scores 24–32, because
scoring high requires restating the same rule four to six ways) and the regex
precision pass are both known defects, deliberately **not** fixed here: they
change every score, and bundling a scoring change into the release headlined
"we corrected our claims" would muddle both messages.

---

## [0.2.7] — the last public release

**If you are upgrading, you are almost certainly coming from 0.2.7.** It is the
newest version on PyPI; `0.3.0` and `0.3.1` were developed and tagged in-repo
but **never published**, so no released version ever carried the `0.3.x`
behavior. Everything listed under 0.4.0 above is therefore a change relative to
0.2.7, including two that predate the 0.3.x work:

- **The length bonus is gone.** 0.2.x added score for longer prompts. It
  rewarded exactly the padding the Context Bloat detector now flags, and it is
  the reason 0.2.x scores are not comparable to 0.4.0 scores. Expect your score
  to move, usually down.
- **Rules with measured false positives were removed**, so the rule set is not
  a superset of the one you have.

Do not compare a 0.2.7 number to a 0.4.0 number. They are different rulesets
measuring the same thing with different instruments — and per
[`docs/validation.md`](docs/validation.md), neither number ranks prompt quality.
