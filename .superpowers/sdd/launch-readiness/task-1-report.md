# Task 1 Report: Launch-Readiness Canonical Launch Copy + Deterministic Dist Pack

## Status
- Scope complete: Task-1 fix-round 1 contract updates applied in this isolated worktree.
- Final verification: `530 passed, 1 skipped`.
- Canonical launch source is now tracked and used from `docs/launch-copy.json`.
- Checksums contract now excludes `checksums.txt` from its own digest list and is explicitly encoded in `manifest.json`.

## Initial findings carried into this fix
- Independent review flagged one ignored launch source under `docs/launch/launch-copy.json` (clean checkout gap).
- Independent review flagged checksums-self-inclusion and non-canonical checksum validation.
- Independent review flagged unsafe-copy wording and insufficient source-tracking proof in tests.

## Implementation and fixes
- Canonical source moved from ignored `docs/launch/launch-copy.json` to tracked `docs/launch-copy.json`.
- `scripts/generate_dist_pack.py`
  - source path updated to `docs/launch-copy.json`.
  - checksum contract changed to hash only:
    - generated channel artifacts
    - `manifest.json`
  - `checksums.txt` is excluded from its own digest list.
  - `manifest.json` now includes:
    - `checksum_includes: [ ... ]`
    - `checksum_excludes: ["checksums.txt"]`
- `tests/test_launch_copy.py`
  - added git-track contract test for `docs/launch-copy.json`
  - added explicit checksum filename and digest verification from final bytes for both temp builds
  - enforced checksum exclusion of `checksums.txt`
  - strengthened unsupported-claim checks to block “safer prompts” framing and keep explicit safety-compliance negations from being flagged
- `tests/test_release_automation.py`
  - added strict checksum-file parsing and recomputation checks
  - added exclusion assertion for `checksums.txt`
- `docs/automation.md`
  - updated generated distribution source note to `docs/launch-copy.json`.
- Regenerated launch outputs locally under:
  - `C:\wt\crewscore\launch-measurement-v069\_production\launch\dist-pack`
- Removed ignored temp dirs:
  - `C:\wt\crewscore\launch-measurement-v069\_production\tmp-launch-a`
  - `C:\wt\crewscore\launch-measurement-v069\_production\tmp-launch-b`

## Commit chain
- `f0dfea4` — Fix launch source tracking and checksums contract
- `e08ad10` — Update this report with the verified fix chain and final test evidence
- This report does not attempt to embed the hash of a commit that contains itself; use `git log -- .superpowers/sdd/launch-readiness/task-1-report.md` for later bookkeeping commits.

## Actual verification
- Focused launch tests:
  - `.venv\Scripts\python.exe -m pytest tests/test_launch_copy.py tests/test_release_automation.py`
  - Result: `9 passed`
- Full tests:
  - `.venv\Scripts\python.exe -m pytest`
  - Result: `530 passed, 1 skipped`
- Generation:
  - `.venv\Scripts\python.exe scripts\generate_dist_pack.py`

## Remaining concerns
- `_production` remains intentionally gitignored; generated artifacts are not committed by this task.
- `CHANGELOG.md` and historical version/changelog context remain unchanged (0.6.9 preserved).
