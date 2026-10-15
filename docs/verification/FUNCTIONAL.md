# Functional verification

What CrewScore does for each kind of user, the rules it enforces, and where it
stops. Evidence for each journey is in [COVERAGE.md](COVERAGE.md). Nothing here
was executed in this pass. Command text and behavior come from reading the code
at `e9a1c9b` (file:line given where it matters) and from [cli](../cli.md),
[policies](../policies.md) and [github-action](../github-action.md).

## Roles

There is no authentication, no accounts and no permissions model. Three usage
roles:

| Role | Surface | What they do |
|---|---|---|
| Local CLI user | `crewscore` on their own machine | Score, scan, fix, export, baseline |
| CI maintainer | `action.yml` or the CLI inside a pipeline | Gate pull requests on named controls |
| Browser-checker visitor | https://crewscore.ai/ | Paste a prompt, review gaps, apply control wording, rescore |

## Journeys

| # | Journey | Exact command or action |
|---|---|---|
| 1 | Score one prompt | `crewscore test -f prompt.md` (add `--json`, `--explain`, `--report out.html --badge b.svg`) |
| 2 | Score an inline string | `crewscore test --prompt "You are a helpful assistant..."` |
| 3 | Gate on one control | `crewscore test -f prompt.md --require human_gate.approval_required` |
| 4 | Scan a repository | `crewscore scan .` (add `--json`, `--summary`, `--sarif crewscore.sarif`) |
| 5 | Gate a repo on controls | `crewscore scan . --require human_gate,safe_stop` |
| 6 | Gate coding-agent config | `crewscore scan . --max-smells 0` |
| 7 | Preview fixes | `crewscore fix --prompt-file p.md --plan` (writes nothing) |
| 8 | Apply fixes | `crewscore fix --prompt-file p.md --apply`, or `--output guarded.md` |
| 9 | Read the rules | `crewscore rules`, `crewscore rules --concepts`, `crewscore rules --json` |
| 10 | Start a policy | `crewscore init .` (refuses to overwrite without `--force`) |
| 11 | Record a baseline | `crewscore baseline . --output .crewscore-baseline.json` |
| 12 | Block regression | `crewscore scan . --baseline .crewscore-baseline.json --fail-on-regression` |
| 13 | Hand off to live testing | `crewscore export-eval --prompt-file p.md --output-dir ./crewscore-eval` |
| 14 | Vendor checklist | `crewscore assess-vendor --name "Acme AI" --answers "y,y,n,dk,y,y,n,y,n,y"` |
| 15 | CI via Action | `uses: shmindmaster/crewscore@v2` with `scan-path` or `prompt-file`, `required-controls`, `sarif` |
| 16 | Browser check | Open crewscore.ai, paste a prompt, review the first gap, apply the wording, see the count rise |
| 17 | Rebuild the demo | `python scripts/build_demo_workspace.py ./demo-workspace` |
| 18 | Re-derive validation | `python scripts/validate_corpus.py` (fetches third-party corpora at pinned SHAs) |

Journey 3 on a prompt missing the control exits 2 and prints a
"Required-control failure" line. After the sentence is added it exits 0 and
prints "REQUIRED CONTROL COVERED ... (the text states it; not proof the agent
obeys it)". This is the sequence in the delivered film; see
[DEMOS.md](DEMOS.md). The line-by-line path is in
[TECHNICAL.md](TECHNICAL.md#critical-feature-trace).

## Business rules

- **23 controls in 8 dimensions.** Injection, hallucination, citation, cost,
  human gate, safe stop, audit, compliance. The control list is `CONCEPTS` in
  `crewscore/scorers/structural_analysis.py:462`.
- **Coverage, not quality.** Per-dimension score is
  `(100 x covered + N // 2) // N`; overall is the floor of the mean of the 8.
  No length term, no floor. A control counts once however many phrasings match.
  Formula in [scoring-and-controls](../scoring-and-controls.md).
- **Two artifacts, two rulesets.** Classification uses the file name and path
  only, never content (`crewscore/profiles.py:74`). `AGENTS.md`, `CLAUDE.md`,
  `.cursorrules`, `.cursor/rules/*`, `copilot-instructions.md` and similar are
  coding-agent config: configuration smells only, **no governance score**.
  `--json` omits `overall`, `dimensions`, `findings` and `transparency` for
  them. `--threshold` is ignored for config and says so (`cli.py:414`,
  `cli.py:660`). `--profile` is the only override.
- **Smells are advisory.** They never change the score. `--max-smells N` is the
  separate gate.
- **Fix never writes governance text into config.** `fix` refuses on config
  (exit 1). Forcing it with `--profile system_prompt` records
  `forced_governance_write: true`.
- **Machine output is prompt-free.** JSON, summary, sticky PR comment, SARIF
  and baselines carry rule IDs, dimensions, status and control labels only.
  `findings_export.public_findings` is the single gate. `--include-snippets` is
  a deprecated escape hatch and never applies to SARIF.
- **Policy beats averages.** `--require` accepts a control ID or a whole
  dimension; an unknown selector is a policy error (`policy.py:66`).
  Regression fails only when a control recorded in the baseline disappears. A
  new file with no baseline entry is reported, not failed.
- **Provenance is declared.** Each dimension is graded evidence-backed,
  plausible or author-intuition. Cost, Compliance and Audit have disclosed thin
  construct validity ([validation](../validation.md)).

## Error handling

| Exit | Meaning | Source |
|---|---|---|
| 0 | Ran; no gate failed | default |
| 1 | Input or usage problem: neither `--prompt` nor `--prompt-file` (`cli.py:380`); unreadable or oversized file (`cli.py:71-100`); policy error such as an unknown control (`cli.py:146`, `:154`); `fix` refusal on config; `init` refusing to overwrite (`cli.py:1394`); `scan` finding no candidate files (`cli.py:1633`) | `crewscore/cli.py` |
| 2 | A gate failed: `--threshold` (`cli.py:659`), `--max-smells` (`:681`), required or forbidden control missing, or regression (`:694`); in `scan`, any failed file (`:1939`) | `crewscore/cli.py` |

Click's own argument errors (for example `--threshold 101`) follow click's
convention and were not exercised.

Failure reasons go to stderr even under `--json`, so stdout stays pure JSON.

Discovery refusals (`crewscore/pathsafe.py`): symlinks and junctions are never
followed or read, and the walk never leaves the chosen root. Each refusal is
reported on stderr (under `--json`, one `skipped_unsafe_path` object each) and
never added as a result row, so an empty result is not mistaken for a clean
tree. There is no opt-in. Files over the size cap are rejected with a message,
not a traceback.

Action behavior (`action.yml`): if CrewScore crashes and emits non-JSON, the
`scored` output stays empty, so consumers must test `scored == 'true'`. A failed
sticky-comment post (no `pull-requests: write`, or a fork PR) degrades to a
warning.

## Known gaps

- **No runtime enforcement.** Coverage says the text states a control. It does
  not show the agent obeys it. There is no live adversarial testing. For that,
  `export-eval` writes Promptfoo and garak starters and does not run them.
- **Thin construct validity** for the Cost, Compliance and Audit dimensions.
- **No MCP surface** and **no framework adapters.** LangGraph, CrewAI and
  similar are roadmap items ([roadmap](../roadmap.md)).
- **The browser checker cannot detect two smells.** Init Fossilization needs git
  history and Lint Leakage needs the repo. The payload says so
  (`web_export.py`, `BROWSER_UNDETECTABLE_SMELLS`).
- **Classifier is filename-based.** A system prompt saved as `AGENTS.md` is
  treated as config unless `--profile` overrides it.
- **Alpha.** The `pyproject.toml` classifier is Development Status 3 - Alpha.
  The `--json` shape and exit codes are treated as contract but change at minor
  versions ([CHANGELOG](../../CHANGELOG.md)).
- **Not checked here:** the runtime behavior of any command in this pass. See
  [TESTS.md](TESTS.md).
