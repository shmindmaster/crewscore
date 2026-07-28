# Plan: Preflight completion slice (SDD + TDD)

**Repo:** `C:\Repos\shmindmaster\crewscore`  
**Branch:** `feat/preflight-completion` (off main)  
**Goal:** Finish audit leftovers with TDD-backed, shippable product work — CLI fix plan parity, locked UX contracts, metrics module, export completion, 0.2.6.

## Global constraints

- TDD: failing test first for every production behavior change.
- Honesty: structural pre-gate only; no red-team / certification claims.
- Keep existing HTML contract strings: builder-first hero, "Vendor checklist (self-attest)", not-a-red-team, templates inflate.
- Web scoring stays offline (`score-engine.js`); no LLM SDKs.
- Tests: `py -3.13 -m pytest` must stay green.
- Prefer small commits per task.
- Do not force-push main; work on feature branch; PR or merge when green.

## Tasks

### Task 1 — CLI fix plan / dry-run (agentic parity with web)

**Why:** Web has plan→apply; CLI `fix` still mutates or dumps with less control.

**TDD:**
1. RED: `test_fix_plan_json_lists_dimensions_without_writing` — `crewscore fix --prompt-file X --plan --json` exits 0, lists `fixes_planned` keys, does not change file.
2. RED: `test_fix_plan_human_lists_dimensions` — human output mentions planned dimensions / "plan" language.
3. GREEN: implement `--plan` / `--dry-run` on `fix` command.
4. RED/GREEN: without `--plan` or `--apply`/`--output`, behavior unchanged (print enhanced prompt).

**Files:** `crewscore/cli.py`, `tests/test_cli.py`, optionally thin helper in `scorers/fix_patterns.py`.

**Done when:** pytest for plan flags pass; applying still works.

---

### Task 2 — Web UX contract tests (lock preflight workflow)

**Why:** Audit F1–F5 implemented in HTML without strong regression tests.

**TDD:**
1. RED tests in `tests/test_web_ux.py` asserting `index.html` contains:
   - stage markers: Prompt / Inspect / Act / Export (or `stg-prompt` … `stg-export`)
   - "Plan fix" or plan-before-mutate language
   - "Apply plan" and Cancel
   - capability stamp "Structural pre-gate"
   - vendor secondary (not equal primary tab list as only chrome)
   - `crewscore_metrics_v1` or track() privacy events
2. GREEN: only if HTML missing pieces — fix HTML to match; do not remove honesty strings.

**Files:** `tests/test_web_ux.py`, possibly `index.html`.

**Done when:** new tests pass; existing vendor/web_engine tests pass.

---

### Task 3 — Privacy-safe metrics module (testable pure core)

**Why:** F8 — metrics only inlined in index.html; untestable.

**TDD:**
1. RED: pure functions in Python or small JS-testable contract — prefer Python helper `crewscore/metrics.py`:
   - `bucket_score(n) -> str` buckets
   - `append_event(store, event, props, *, max_events=200) -> store` no prompt keys allowed
   - `assert_privacy(props)` rejects keys like `prompt`, `text`, `body`
2. GREEN: implement module; wire optional CLI `crewscore` does not require metrics.
3. Document web localStorage schema matches event names in `_product-experience/06-outcome-measurement-plan.md`.

**Files:** `crewscore/metrics.py`, `tests/test_metrics.py`, doc touch if needed.

**Done when:** metrics unit tests pass; no prompt capture.

---

### Task 4 — Export completion checklist + reduced-motion

**Why:** F7 success state incomplete; a11y floor.

**TDD:**
1. RED: `test_web_ux` asserts export deck has completion checklist markers (e.g. `export-checklist` or three completion items: share/CI/prompt).
2. RED: CSS or HTML has `prefers-reduced-motion` rule.
3. GREEN: update `index.html` export stage + CSS.

**Files:** `index.html`, `tests/test_web_ux.py`.

**Done when:** tests pass.

---

### Task 5 — Version 0.2.6 + README CLI docs + ship

**Why:** Surface new `--plan` flag; ship coherent release.

**TDD:**
1. RED: version string expectations if any (prefer dynamic RULESET/version tests already).
2. GREEN: bump `__version__` / pyproject to 0.2.6; export web engine; README documents `crewscore fix --plan`.
3. Run full pytest; commit; open PR or merge to main; tag/publish only if existing publish pattern allowed (PyPI via 1Password).

**Files:** `crewscore/__init__.py`, `pyproject.toml`, `README.md`, `score-engine.js`, AGENTS.md if needed.

**Done when:** full suite green; package version 0.2.6; docs mention plan.

## Parallelism note

Tasks 1 and 3 are file-independent (can parallel via worktrees).  
Tasks 2 and 4 share `index.html` / `test_web_ux.py` — sequential after 1 or with 1 done.  
Task 5 last.
