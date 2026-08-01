# CrewScore 0.6.10 release-candidate report

Status: DONE — local candidate only; no push, tag, publication, deployment, or floating-tag move performed.

## Commit boundary

- Exact base: `c2c23a20f77b94d62998a048b51a6da25d2b9ab9`
- Branch: `worktree-release-v0610-main`
- Release-candidate commit: the commit containing this report
- Independent-review P2 remediation: the follow-up commit containing this
  report update
- Hosted privacy-copy remediation: the follow-up commit containing this report
  update

## Outcome

Prepared the truthful `0.6.10` patch candidate across package metadata, the
Python version, generated browser engine, validation documents, changelog,
privacy copy, measurement documentation, deterministic launch-copy checksum
contracts, and release-operation documentation.

The scoring implementation did not change. The generated browser engine still
reports `crewscore-hygiene@0.6.0`, 23 controls, and 8 dimensions. Its only
generated-source diff is `0.6.9` to `0.6.10`.

Every allowlisted PostHog capture body now carries immutable
`$geoip_disable: true` and `$process_person_profile: false`. These are fixed
transport properties rather than caller properties: the strict schema rejects
caller attempts to set them, the capture builder applies them after validated
properties, and Python/JavaScript schema parity exposes the same contract.
The independent-review regression invokes every allowlisted event, inspects
every actual serialized request body, attempts caller overrides of both fixed
properties, and proves neither attempt emits an extra request.
Existing prompt-content rejection, coding-configuration versus governance
separation, optional `traffic_class`, opt-out, non-production suppression, and
silent hero autoplay remain covered.

Windows generation of `score-engine.js` was found to translate LF to CRLF and
create a false whole-file release diff. The generator now requests LF
explicitly, with a regression test. Regeneration is byte-stable across Windows
and Linux.

## Deterministic launch artifacts

The canonical demo asset and launch distribution pack were regenerated from
repository scripts. The demo SVG remained byte-identical. The ignored working
pack is retained at `_production/launch/dist-pack` for release evidence.

- Package version: `0.6.10`
- Ruleset: `crewscore-hygiene@0.6.0`
- Corpus: 356 prompts
- Posts automatically: `false`
- `checksums.txt` SHA-256: `7a6a016e91b9e37edac913bd3e95e88a63922e22dc2ae6c5f8ad29b1b68f57e8`
- `manifest.json` SHA-256: `7f43d41451fb96dc4a37c67cd457a0e2caed74b5943a819f41b11e821682eb32`
- Launch-copy source SHA-256: `079466aea3cdf559636b8b4e52c14873e6008352635a350d8e8f3d9c5cd5d37f`

All seven checksum rows were recomputed from disk and matched.

## TDD and verification

- Red: version test expected `0.6.10` and observed `0.6.9`.
- Red: every-allowlisted-event capture test observed no `$geoip_disable`.
- Green focused contract gate: 4 passed.
- Release-focused Python gate: 213 passed, 1 skipped.
- Full Python gate: 585 passed, 2 skipped.
- Full browser gate with retries disabled: 127 passed, 21 expected project
  skips across Chromium, Firefox, WebKit, and mobile Chromium.
- `python -m build`: built `crewscore-0.6.10.tar.gz` and
  `crewscore-0.6.10-py3-none-any.whl`.
- `python -m twine check`: wheel and sdist passed.
- Fresh Windows venv, pip cache disabled: installed the built wheel; CLI
  reported `0.6.10`; rules reported `crewscore-hygiene@0.6.0`; governance
  output contained an integer aggregate; coding-config output had
  `governance_applicable: false` and no `overall` or `scores`; the installed
  package rendered a browser engine byte-identical to the committed engine.
- Fresh `python:3.13-slim` Linux container, pip cache disabled: installed the
  same wheel and passed the release workflow's version, governance,
  coding-config, rules, and no-LLM assertions.
- `git diff --check`: clean.
- Stale-version search: only the historical changelog, explicit 0.6.9
  compatibility comments, and stale-version regression lists retain `0.6.9`.
- Independent-review P2 TDD mutation: temporarily changing the fixed
  `$process_person_profile` value to `true` made the new actual-body regression
  fail; restoring `false` made it pass. The mutation was not retained.
- Independent-review focused analytics/schema/privacy gate: 77 passed.
- Independent-review full Python gate: 586 passed, 1 environment-dependent
  skip.
- Independent-review browser privacy/analytics gate with retries disabled: 12
  passed across Chromium, Firefox, WebKit, and mobile Chromium.
- The P2 runtime-test remediation changes only the runtime regression and this report;
  package artifacts, launch copy, and distribution checksums are unaffected.
- Hosted privacy-copy TDD: the privacy-page and canonical-launch-copy
  regressions both failed before the copy change and passed afterward.
- The privacy page now says every allowlisted request disables PostHog GeoIP
  enrichment and does not create a PostHog person profile. The canonical Show
  HN draft says the same in plural form. Neither statement claims an
  account-wide or server configuration.
- Hosted-copy focused release/privacy/analytics gate: 104 passed.
- Hosted-copy full Python gate: 586 passed, 1 environment-dependent skip.
- Hosted-copy browser privacy/offline and mobile-subpage gate with retries
  disabled: 5 passed, 3 expected project skips.
- Regenerated-pack verification: all 7 checksum rows matched the retained
  files; only the canonical Show HN draft and its derived manifest/hash
  surfaces changed.

## Release-time gates not performed

This candidate does not authorize production mutation. After merge and exact
main-branch CI, the release operator must create annotated tag `v0.6.10` at the
verified main SHA, verify PyPI and GitHub Release artifact parity, and confirm
the release workflow moves floating Action tags `v1` and `v2` to that same
SHA. Production website SHA, live privacy/analytics payloads, PostHog project
schema, and user-session evidence remain separate launch gates.
