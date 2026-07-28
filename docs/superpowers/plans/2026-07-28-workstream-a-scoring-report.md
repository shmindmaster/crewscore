# Workstream A — Scoring authenticity report

**STATUS**: DONE  
**Branch**: `feat/scoring-authenticity-0.2.2`  
**Commit**: `c595d34` — `feat: authentic scoring — ruleset, rule IDs, anti-gaming, structural tiers`

## Behaviors (TDD)

### 1. RULESET_ID + ScoreResult.ruleset / warnings

- **Test**: `test_ruleset_id_constant`, `test_build_result_includes_ruleset_and_warnings`, `test_test_json_output`
- **RED**: `ImportError: cannot import name 'RULESET_ID'`; `KeyError: 'ruleset'`
- **Impl**: `RULESET_ID = "crewscore-hygiene@0.2.2"` in `crewscore/scoring.py`; `ScoreResult` fields `ruleset`, `warnings`
- **GREEN**: all related tests pass

### 2. Stable rule_ids on findings

- **Test**: `test_matched_findings_include_rule_id`, `test_missing_findings_include_rule_id_for_labeled_signals`
- **RED**: `assert None` on `f.get("rule_id")`; empty labeled missing list
- **Impl**: patterns as `(rule_id, regex)` tuples e.g. `injection.01`; findings include `rule_id` when known
- **GREEN**: pass

### 3. Anti-gaming template boilerplate

- **Test**: `test_template_boilerplate_warning_on_crewscore_fix`, `test_bare_prompt_no_template_warning`, `test_test_json_template_warning_after_fix`
- **RED**: missing warnings key / no detection
- **Impl**: `detect_template_boilerplate()` on FIX_TEMPLATES headers + `CrewScore` markers → `template_boilerplate_detected`
- **GREEN**: pass

### 4. Soften broad injection pattern

- **Test**: `test_bare_safety_word_does_not_inflate_injection`
- **Impl**: replaced bare `safety|guardrail|boundar` with defense-context patterns
- **GREEN**: bare "safety guidelines" → injection &lt; 40

### 5. Structural tier labels

- **Test**: `test_build_result_tier` updated
- **RED**: old `"PRODUCTION READY"` etc.
- **Impl**: STRONG / OK WITH GAPS / WEAK / CRITICAL GAPS; JS `scoreTier` synced
- **GREEN**: pass

### 6. Version 0.2.2

- **Test**: `test_version`
- **RED**: `assert '0.2.2' in '…0.2.1…'`
- **Impl**: `pyproject.toml` + `__init__.py`
- **GREEN**: pass

### 7. Web export

- `python scripts/export_web_engine.py` regenerated `score-engine.js` with `ruleset`, `[rule_id, pattern]` pairs, structural tiers, boilerplate detection

## Test evidence

```
py -3.13 -m pytest -q
77 passed in 0.41s
```

## Files changed

- `crewscore/scoring.py`
- `crewscore/scorers/structural_analysis.py`
- `crewscore/cli.py` (pass `prompt_text` into `build_result`)
- `crewscore/web_export.py`
- `crewscore/__init__.py`
- `pyproject.toml`
- `score-engine.js`
- `tests/test_structural_analysis.py`
- `tests/test_explain.py`
- `tests/test_cli.py`

## Merge conflicts expected

- **`crewscore/cli.py`**: workstream B (scan command) will also edit this file — likely conflict on imports / command registration near `test` command. Scoring change is small: only `build_result(..., prompt_text=system_prompt)`.
- **`pyproject.toml` / `__init__.py` version**: both streams may bump 0.2.2 — trivial conflict.
- **`score-engine.js`**: regenerate after merge via `python scripts/export_web_engine.py`.

## Out of scope (not done)

- Scan command (B)
- index.html product surface (C)
- README tier table copy (left to C; code tiers already structural)
