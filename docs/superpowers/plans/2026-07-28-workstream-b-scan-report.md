# Workstream B — `crewscore scan` report

**STATUS**: DONE  
**Commit**: `f948f38`  
**Branch**: `feat/scoring-authenticity-0.2.2`

## Files changed

| File | Change |
|------|--------|
| `crewscore/scan.py` | **new** — `discover_prompt_files`, `score_paths` |
| `crewscore/cli.py` | wire `@main.command("scan")` |
| `tests/test_scan.py` | **new** — 16 TDD tests |

## How to run

```bash
# from repo root (after pip install -e ".[dev]")
crewscore scan
crewscore scan ./path/to/repo
crewscore scan . --json
crewscore scan . --threshold 50
crewscore scan . --explain
crewscore scan . --json --threshold 70
```

Exit codes:
- `0` — files found, all scores ≥ threshold (or no threshold)
- `1` — no agent prompt files found
- `2` — at least one file scored below `--threshold`

## Discovery rules

**Known basenames** (anywhere under root):  
`AGENTS.md`, `CLAUDE.md`, `system-prompt.md`, `system_prompt.md`, `AGENT.md`, `prompts.md`

**Under dirs named** `agents` / `prompts` / `prompt`:  
`*.md`, `*.txt`, `*.yaml`, `*.yml`

**Skipped dirs**: `.git`, `node_modules`, `venv`, `.venv`, `dist`, `__pycache__`, `.tox`, `site-packages`  
**Size cap**: 500KB  
**Depth**: max 8 from root

## TDD evidence

### Behavior 1 — discover known names

**Test** (`tests/test_scan.py::test_discover_known_names`): asserts six known basenames found; README.md excluded.

**RED** (stub `NotImplementedError`):
```
tests/test_scan.py::test_discover_known_names FAILED
E   NotImplementedError
C:\Repos\shmindmaster\crewscore\crewscore\scan.py:10: NotImplementedError
```

**Implementation**: `discover_prompt_files` walks tree, matches `KNOWN_NAMES`.

**GREEN**: PASSED

### Behavior 2 — discover under prompt dirs

**Test**: `test_discover_under_prompt_dirs`  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 3 — skip excluded dirs

**Test**: `test_discover_skips_excluded_dirs`  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 4 — skip huge files

**Test**: `test_discover_skips_huge_files` (>500KB)  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 5 — sorted unique

**Test**: `test_discover_returns_sorted_unique`  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 6 — empty repo

**Test**: `test_discover_empty_repo`  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 7 — score_paths overall/tier/dimensions

**Test**: `test_score_paths_returns_overall_and_tier`  
**RED**: NotImplementedError at score_paths  
**GREEN**: PASSED (guarded prompt scores higher than bare)

### Behavior 8 — score_paths preserves path

**Test**: `test_score_paths_preserves_path`  
**RED**: NotImplementedError  
**GREEN**: PASSED

### Behavior 9 — CLI JSON

**Test**: `test_scan_cli_json`  
**RED**:
```
Error: No such command 'scan'.
assert 2 == 0
```
**GREEN**: PASSED — list of `{path, overall, tier, dimensions}`

### Behavior 10 — CLI human table

**Test**: `test_scan_cli_human_table`  
**RED**: No such command 'scan'  
**GREEN**: PASSED

### Behavior 11 — no files → exit 1

**Test**: `test_scan_cli_no_files_exit_1`  
**RED**: exit 2 (unknown command)  
**GREEN**: PASSED exit 1

### Behavior 12 — threshold → exit 2

**Test**: `test_scan_cli_threshold_fails_exit_2`  
**RED**: JSONDecodeError (no scan command)  
**GREEN**: PASSED exit 2

### Behavior 13 — threshold pass

**Test**: `test_scan_cli_threshold_passes`  
**RED**: No such command  
**GREEN**: PASSED

### Behavior 14 — default path cwd

**Test**: `test_scan_cli_default_path_is_cwd`  
**RED**: No such command  
**GREEN**: PASSED

### Behavior 15 — explain optional

**Test**: `test_scan_cli_explain_optional`  
**RED**: No such command  
**GREEN**: PASSED

### Behavior 16 — CLI skips node_modules

**Test**: `test_scan_skips_node_modules_in_cli`  
**RED**: No such command  
**GREEN**: PASSED

### Full RED session summary

```
16 failed in 0.11s
```
All failures: `NotImplementedError` (library) or `No such command 'scan'` (CLI).

### Full GREEN session

```
pytest tests/test_scan.py -v
============================= 16 passed in 0.14s ==============================
```

### Neighbour CLI regression check

```
pytest tests/test_scan.py tests/test_cli.py::test_test_threshold_fails \
  tests/test_cli.py::test_test_requires_input \
  tests/test_cli.py::test_fix_requires_input \
  tests/test_cli.py::test_assess_vendor_json -v
============================= 20 passed in 0.15s ==============================
```

## Concerns (out of scope)

- Suite has pre-existing failures from incomplete workstreams A/C/D (`RULESET_ID`, action `scan-path`, index.html hero, version 0.2.2). Not introduced by this commit.
- Tiers still use existing labels (`PRODUCTION READY` etc.); workstream A will rename to structural tiers.
- `ruleset` key is included in JSON only when `RULESET_ID` exists (workstream A).
- Plan also mentioned `*.system.md` and `.json` under prompt paths; brief listed specific names/extensions — followed the task brief.
