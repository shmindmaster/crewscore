# Task 6 broken-symlink ancestor closure

## Outcome

- Output validation now rejects a symlink ancestor based on the link itself, even when its target is missing and `Path.exists()` is false.
- Normal output-directory creation and pack generation behavior are unchanged.

## TDD evidence

- Added a real broken directory symlink ancestor regression before changing production code.
- The initial focused run failed as expected: the generator bypassed the guard and crashed while trying to create directories through the broken link instead of emitting the fail-closed symlink refusal.
- After the one-condition implementation change, the new regression and all launch-pack tests passed.

## Validation

- `py -m pytest tests/test_launch_copy.py::test_generate_dist_pack_refuses_broken_symlink_output_ancestor -q` — 1 passed.
- `py -m pytest tests/test_launch_copy.py -q` — 21 passed.
- `py -m pytest -q` — 580 passed, 1 skipped.
- `git diff --check` — passed (Git reported only the repository's Windows line-ending notices).

## Scope and delivery state

Only `scripts/generate_dist_pack.py`, the focused launch-copy regression test, and this report changed. No scoring, analytics, browser behavior, ruleset, version, dependencies, hero, or release surface changed. This is implemented and locally validated only; it has not been pushed, merged, or deployed.
