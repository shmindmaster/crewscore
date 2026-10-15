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
