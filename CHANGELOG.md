# Changelog

All notable changes to CrewScore are documented here.

This project follows [Semantic Versioning](https://semver.org/). The `--json`
payload shape, the CLI exit codes, and the GitHub Action's outputs are treated
as the public contract; breaking changes to any of them get a minor bump
pre-1.0 and are listed under **Breaking** below.

---

## [0.4.0] — 2026-07-28

The honest reframe. CrewScore measures **coverage**, not quality — we tested
that claim against 1,368 real system prompts, it did not hold, and this release
publishes the study rather than the marketing.

### Added

- **`docs/validation.md` — the validation study.** Against 283 production
  prompts and 1,085 amateur ones, the scorer does not separate the two once
  length is controlled (Cliff's delta +0.061, 95% CI −0.050 to +0.172, p=0.36).
  Character count alone is the better classifier (AUC 0.863 vs 0.800). No file
  in the corpus scores above 50/100. The document also reports the aggregation
  defect behind the empty upper scale, the regex precision problem behind the
  discrimination failure, and per-dimension construct validity — including the
  three dimensions (`cost`, `compliance`, `audit`) now shipping with **known-poor
  validity, disclosed rather than quietly dropped**. No prompt text is
  redistributed; aggregate statistics only.
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

- **Ruleset is now `crewscore-hygiene@0.4.0`.** 0.3.1 was never published, so no
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
scoring high requires restating the same rule five or six ways) and the regex
precision pass are both known defects, deliberately **not** fixed here: they
change every score, and bundling a scoring change into the release headlined
"we corrected our claims" would muddle both messages.

---

## [0.3.0] — earlier

Last publicly released version. Offline deterministic scoring across eight
governance dimensions, CLI + web engine, GitHub Action with a threshold gate.

*(0.3.1 was tagged internally during development and never published.)*
