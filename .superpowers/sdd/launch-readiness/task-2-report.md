# Task 2 Report: launch measurement and deterministic assets

## Scope and state

- Isolated worktree: `C:\wt\crewscore\launch-measurement-v069`
- Branch: `agent/launch-measurement-v069`
- Comparison: `origin/main..HEAD`
- No push, PR, deploy, package publish, or external announcement was performed.

## Implemented outcome

- The demo asset is generated from the tracked Northstar fixture and live scorer, proving a deterministic written-control change from `8 / 23` to `9 / 23`.
- `docs/demo.svg` is valid standalone SVG: count suffixes and wrapped gap lines use SVG `tspan` elements, and the real `image/svg+xml` browser test checks all expected text plus panel bounds.
- Demo and launch-pack files are canonical UTF-8/LF bytes with pinned SHA-256 regression fixtures.
- Launch-pack generation is transactional across the candidate, backup, promotion, and rollback phases. Unrelated regular files and symlinks are preserved; symlinks are not dereferenced during staging.
- Browser-bound telemetry retains strict event schemas and bounded values. Coding-agent configuration checks emit `cs_check_completed` without a governance score.
- The published `0.6.9` Python API remains compatible: `validate_props` and `validate_event` keep their forbid-only/sparse-safe behavior, `append_event` preserves safe local properties, and `schema_payload` retains the legacy string score buckets and `network` field. `validate_capture_event` is the separate strict capture-boundary validator.
- Launch measurement guidance continues to distinguish telemetry from activation, adoption, and product-market-fit evidence.

## Final verification evidence

- `.venv\Scripts\python.exe -m pytest -q tests\test_demo_asset.py tests\test_metrics.py tests\test_launch_copy.py` -> `52 passed`.
- `.venv\Scripts\python.exe -m pytest` -> `566 passed, 1 skipped`.
- `npm run test:web -- --project=chromium` -> `21 passed`.
- `npm run test:web` -> `81 passed, 3 skipped` across Chromium, Firefox, WebKit, and mobile Chromium.
- `.venv\Scripts\python.exe scripts\generate_dist_pack.py` -> version `0.6.9`, checksum-file SHA-256 `29bdc527ee30ec4ca25f06a9540b4bc8133ea68f9803d83ae88350002ce22deb`.
- `docs/demo.svg` SHA-256 -> `9e274ac414f89ed210edc2d5266ddf8a2ff7d712652f01bf8609fce648c8ec8b`.
- `git diff --check` -> passed.

## Artifact and source paths

- `docs/demo.svg`
- `scripts/generate_demo_asset.py`
- `scripts/generate_dist_pack.py`
- `_production/launch/dist-pack/` (generated locally and gitignored)
- `docs/launch-measurement.md`
- `crewscore/metrics.py`

## Remaining gates

- Independent terminal review of the final branch head.
- Merge/CI validation on the exact reviewed head.
- Clean-machine installation and production-site verification.
- Real user sessions and launch-channel results; automated tests do not establish product-market fit.

## Traceability

- The authoritative implementation range is `origin/main..HEAD` on `agent/launch-measurement-v069`.
- The final remediation commit is the commit containing this report; use `git log -1 --oneline` in the isolated worktree for its immutable SHA.
