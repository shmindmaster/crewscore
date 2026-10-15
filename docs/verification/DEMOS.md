# Demos

Every film below is a **real recording**. Each one ran the installed `crewscore` CLI in a real Git Bash shell against a synthetic fixture repository, captured with headless Playwright (WebM) and finished with Recast (pointer, click and punch-in zoom). There is no mock UI and no substitute footage. The prompt (a support assistant) and its owner ("Ines") are fictional.

Videos are kept outside the repository, in the owner's media library. SHA-256 hashes identify each exact file.

## Delivered films

| Film | Length | Recorded at | What it shows | QA on the exact file | SHA-256 |
|---|---|---|---|---|---|
| `Videos\Portfolio\CrewScore\01 - One Sentence.mp4` (+ `.srt`) | 1:28 | main `e9a1c9b`, 0.6.14, ruleset `crewscore-hygiene@0.6.0` | The `test` run on a one-line prompt prints 0/23 written and FIRST GAP: A human must approve. `fix --plan` proposes templates and writes nothing. `test --require human_gate.approval_required` exits 2. One sentence is added, and the same command exits 0 with "REQUIRED CONTROL COVERED ... not proof the agent obeys it". The film closes on a walkthrough of `crewscore/scorers/structural_analysis.py:204-243` and `:537-549`. | -16.0 LUFS integrated; WER 0.0 (ElevenLabs scribe_v2 vs the authored script); no frozen picture ≥ 4 s; independent story-experience review 88/100 | `0219663d4284509c12220c07e556956a61c00100ffa771ba7914313169e471d6` |
| `Videos\Evergreen\Proof Clips\03 - CrewScore Missing Safeguards.mp4` (+ `.srt`) | 0:12 | cut from the film above | The missing-safeguards scorecard and the fix plan. A modular clip for proposals. | WER 0.0 | `a2ceeb47ce9cffc70be29f2ac6e555ea5d6e98564a112ca7fa0146696e88b1c7` |

Narration is a third-person stock voice: ElevenLabs Bella, `eleven_v4`. The 1:28 film corresponds to format **B** (functional walkthrough) and fits the **A** length (60–90 s). Format **C** (architecture and integration walkthrough) has not been made.

## Traces behind the film
These are in the production workspace `D:\Local-AI\data\artifacts\media-studio\crewscore-hero-r2-20261014\`:
- `receipts/terminal-commands.jsonl`: every command typed on camera, with cwd, exit code and full output.
- `capture/receipt.json`: SHA-256 of each Recast take, plus the events and expectations observed.
- `compose/remotion/public/code.json`: the source lines shown in the walkthrough, extracted from the clone at `e9a1c9b`, with the file hash.
- `qa/QA-RECORD.md`: the gate table and the reviewer's notes.

## Reproduce the demo
```bash
python scripts/build_demo_workspace.py ./demo-workspace
crewscore test -f prompts/<prompt>.md --no-explain
crewscore fix -f prompts/<prompt>.md --plan
crewscore test -f prompts/<prompt>.md --no-explain --require human_gate.approval_required; echo "exit $?"
# add: "A human must approve any refund or account change before it happens."
crewscore test -f prompts/<prompt>.md --no-explain --require human_gate.approval_required; echo "exit $?"
```

## Not demonstrated
- The browser checker at crewscore.ai: it is on the site, but no film covers it.
- The GitHub Action on a real PR (sticky comment, SARIF upload).
- `export-eval` handoff to Promptfoo or garak.

## Production plan: the next two assets

Both reuse the r2 footage. Heavy work (capture, TTS, render) waits for an assigned slot.

**C. Technical deep dive, "How CrewScore decides" (about 6 min, developer education).** Planned, not made.
- **Hook (0:00–0:15).** The same prompt is scored by the CLI (`--json`) and by the browser checker side by side, and both show the same coverage. This is a measured result, and it is enforced by `tests/test_web_engine.py`.
- **Axes (0:15–0:45).** Written coverage versus runtime behaviour. Deterministic regex versus an LLM judge. Prompt-free machine output.
- **Behaviour, then diagram (0:45–3:00).**
  - Show `test --require human_gate.approval_required` failing at exit 2 and passing at exit 0. Reuse r2 takes S04 and S05.
  - Walk the trace in [TECHNICAL.md](TECHNICAL.md#critical-feature-trace) on the code stage: `cli.py` → `analyze_with_findings` → `covered_concepts` → `evaluate_policy` → exit code.
  - Show the Mermaid architecture diagram only after the behaviour has been seen.
- **Validation (3:00–4:00).** The generated corpus report, [docs/validation-corpus.md](../validation-corpus.md): 356 pinned prompts and the published effect size with its confidence interval, read from the file on screen.
- **Trade-off (4:00–4:40).** `export-eval` writes Promptfoo and garak starters and says it does not run them. The tool checks written coverage; it is not runtime proof.
- **Failure and recovery (4:40–5:30).** A real `pathsafe` refusal of a symlinked prompt, or a `--fail-on-regression` baseline failure, then the fix.
- **Payoff (5:30–6:00).** `pip install crewscore` and the Action snippet. One call to action.
- **New captures needed:** browser-checker parity, `export-eval`, the refusal or regression run, and `--json`/SARIF output.
- **Voice:** the local Qwen3-TTS narrator (no ElevenLabs spend), with WER checked by local ASR.

**Vertical short (≤ 45 s, 1080x1920).** Planned, not made.
- Reframed from film 01's hero beat: `--require` exits 2, one sentence is added, it exits 0, and the result reads "not proof the agent obeys it".
- The Recast takes are 2880x1620, so a 9:16 crop of each punch-in stays sharp; no letterboxing.
- Burned-in captions. It reuses the existing Bella lines L06–L10, so there is no new TTS.

**ElevenLabs usage to date (film 01):**
- 17 `eleven_v4` lines, 1,047 characters as shipped. The API's `character-cost` headers total 459 for the current lines.
- Superseded re-renders of L03, L11, L13, L15 and L16 added roughly 300 more characters (estimated).
- No new music bed: the CrewScore bed was reused.
