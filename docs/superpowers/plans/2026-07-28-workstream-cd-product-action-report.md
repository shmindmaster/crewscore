# Workstream C+D — Product surface + Action scan + eval handoff

**STATUS**: DONE  
**Commit**: `98d0e5a676ed5abe6f02a028c5e75ee2eaea2161`  
**Branch**: `feat/scoring-authenticity-0.2.2`  
**Message**: `feat: builder-first product surface, scan Action, eval handoff`

## Files changed

| File | Change |
|------|--------|
| `index.html` | Builder-first hero; demoted vendor tab; authenticity line; secondary tab CSS |
| `README.md` | Scoring charter; `scan` docs; demoted vendor; After CrewScore; softened production language |
| `AGENTS.md` | scan + honesty scoring constraints; layout/docs updates |
| `action.yml` | optional `scan-path`; `prompt-file` not required; XOR validation; min-overall outputs |
| `tests/test_action_manifest.py` | scan-path / XOR / min-overall contract tests |
| `tests/test_vendor.py` | hero / vendor tab / authenticity index.html contracts |
| `docs/next-steps-eval.md` | **new** — Promptfoo / garak honest handoff |
| `.github/workflows/example-ci.yml` | scan-path example comments |

## Behaviors (TDD)

### Behavior 1 — Action `scan-path` optional; `prompt-file` not required

**Test**: `tests/test_action_manifest.py::test_action_scan_path_input_optional_and_prompt_file_not_required`

**RED**:
```
assert 'scan-path:' in text
E   assert 'scan-path:' in 'name: CrewScore\n...prompt-file:\n    required: true...'
```

**Implementation**: `action.yml` inputs — both `prompt-file` and `scan-path` `required: false`; script validates one is set.

**GREEN**: PASSED

### Behavior 2 — Action runs `scan` and takes min overall

**Test**: `test_action_script_runs_scan_when_scan_path_set`

**RED**: missing `scan` branch / `min(` / list handling

**Implementation**: if `scan-path` non-empty → `crewscore scan "$path" --json --threshold ...`; parser handles JSON **list** (actual `scan --json` shape) via `min(..., key=overall)`.

**GREEN**: PASSED

### Behavior 3 — Script requires one of prompt-file or scan-path

**Test**: `test_action_script_requires_prompt_file_or_scan_path`

**RED**: no XOR validation

**Implementation**: `Either prompt-file or scan-path is required` + `exit 1`

**GREEN**: PASSED

### Behavior 4 — Hero builder-first

**Test**: `test_index_html_hero_is_builder_first`

**RED**: missing “Score agent prompts in your browser”

**Implementation**: h1 + sub copy updated

**GREEN**: PASSED

### Behavior 5 — Vendor tab secondary

**Test**: `test_index_html_vendor_tab_is_secondary_self_attest`

**RED**: still “I’m buying AI software”

**Implementation**: label `Vendor checklist (self-attest)` + `.tab-secondary` styles

**GREEN**: PASSED

### Behavior 6 — Authenticity line

**Test**: `test_index_html_authenticity_line_warns_templates_and_not_red_team`

**RED**: no “inflate” / incomplete authenticity

**Implementation**: social-proof line — structural text scan, not red-team, templates can inflate

**GREEN**: PASSED

### Docs (no separate RED cycle)

- README Scoring charter (research principles 1–7)
- `crewscore scan .` UX documented
- Vendor demoted under “secondary”
- After CrewScore → Promptfoo / garak
- Tiers use structural labels
- `docs/next-steps-eval.md` handoff
- AGENTS.md scan + honesty constraints
- example-ci.yml scan comments

## Test evidence

```
py -3.12 -m pytest tests/test_action_manifest.py tests/test_vendor.py -q
17 passed

py -3.12 -m pytest -q
77 passed in 0.37s
```

## Concerns

1. **Scan JSON shape coupling**: Action assumes `scan --json` emits a list of objects with `overall`/`tier` (matches Workstream B). If scan later wraps as `{files: [...]}`, parser still supports `files`/`results` keys.
2. **`scan` must be installed**: Action installs from `github.action_path`; monorepo self-test needs scan on that commit (present on this branch via Workstream B).
3. **No live Action workflow run** in this task — only manifest/unit tests + parser smoke.
4. **XSS / escape contracts** preserved (`escapeHtml` tests still green).
