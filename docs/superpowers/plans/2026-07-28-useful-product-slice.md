# CrewScore useful-product slice (post-research)

## Goal

Make CrewScore a **useful builder tool**: evidence-backed hygiene, hard to game, repo-native scan, vendor demoted. Not questionnaire theater. Not red-team cosplay.

## Version

Bump to **0.2.2** when integrating.

## Workstreams (parallel-safe file ownership)

### A — Scoring authenticity (`crewscore/scorers/`, `crewscore/scoring.py`, related tests, `web_export`)

1. **Ruleset version**: constant `RULESET_ID = "crewscore-hygiene@0.2.2"` included in JSON results and explain output.
2. **Rule IDs**: every scorer pattern gets stable id like `injection.01`, findings include `rule_id` when known.
3. **Evidence**: matched findings must keep snippets; missing findings use human labels + rule_id.
4. **Anti-gaming**:
   - Detect CrewScore fix template markers (`## Prompt Injection Defense`, `CrewScore`, known section headers).
   - Add `warnings: ["template_boilerplate_detected"]` (or similar) on result when templates dominate.
   - Soften/remove overly broad patterns that match almost anything (e.g. bare `safety|guardrail` alone if present as high-value).
   - Cap length bonus is already modest; keep or tighten.
5. **Tier honesty**: change tier strings to structural framing:
   - `STRUCTURAL: STRONG` (≥90), `STRUCTURAL: OK WITH GAPS` (70–89), `STRUCTURAL: WEAK` (50–69), `STRUCTURAL: CRITICAL GAPS` (<50)
   - Or keep old tiers but **prefix/suffix** with structural disclaimer in JSON `tier` + human output.
   - Prefer clear structural labels; update all tests.
6. **JSON payload extras**: `ruleset`, `warnings`, findings with `rule_id`.
7. Regenerate `score-engine.js` via `python scripts/export_web_engine.py`.
8. TDD: tests first for rule_id, ruleset, gaming warning, tier labels.

### B — Repo scan (`crewscore/scan.py` new, `cli.py` scan command, tests)

1. `crewscore scan [PATH]` default `.`
2. Discover likely agent instruction files:
   - Names: `AGENTS.md`, `CLAUDE.md`, `system-prompt.md`, `system_prompt.md`, `*.system.md`
   - Paths containing `prompt`, `prompts`, `agents` with extensions `.md`, `.txt`, `.yaml`, `.yml`, `.json` (size cap e.g. 500KB)
   - Skip `node_modules`, `.git`, `venv`, `dist`, `__pycache__`, `.venv`
3. Score each file; print table of path → overall → tier
4. Flags: `--json`, `--threshold` (fail if **any** file below), `--explain` on worst or all
5. Exit 2 if threshold violated; exit 1 if no files found (with helpful message)
6. TDD with tmp_path fixtures

### C — Product surface (README, index.html, AGENTS.md, launch honesty)

1. **Demote vendor**: agent tab primary; vendor secondary smaller tab label "Vendor checklist (self-attest)"
2. Hero copy: builder/repo hygiene first; "not a red-team"; ruleset honesty
3. README: Scoring charter section; `scan` docs; handoff to Promptfoo/garak; demote vendor
4. Footer: still pip + Action

### D — Action + handoff

1. Action optional input `scan-path` OR keep `prompt-file` required but document scan for CI
2. Prefer: if `scan-path` set, run `crewscore scan`; else `prompt-file`
3. Short `docs/next-steps-eval.md`: when to use Promptfoo/garak after CrewScore
4. Update example-ci.yml with scan example
5. test_action_manifest updates

## Integration rules

- Do not break PyPI name or honesty disclaimers
- Never `pip install agent-guard` as this product
- Keep dependency-light (no LLM SDKs)
- After merge: full pytest, export web engine, manual CLI smoke
