# Launch copy

Drafts for the 0.6.0 launch. **Every number here is checked against
[`validation-corpus.json`](validation-corpus.json) by
`tests/test_launch_copy.py`** — if the harness is re-run on a different corpus,
these fail until they are updated. Do not hand-edit a figure.

The numbers you may use:

| Claim | Value | Source |
| --- | --- | --- |
| Corpus size | 356 prompts | 83 production + 273 GPT-Store |
| Production median | 10/100 | `groups.production.describe.median` |
| GPT-Store median | 0/100 | `groups.gpt_store.describe.median` |
| Production prompts scoring 0 | 20/83 | `describe.zeros` |
| Separation | Cliff's δ = 0.614, *p* = 0.0001 | `analysis` |
| Controls | 23 across 8 dimensions | rule catalog |

**What you may not claim.** That the score measures prompt quality, that it
predicts agent behaviour, that a high score means safe, or that any vendor is
bad at this. The finding is that these controls are *rarely written down* — not
that anyone's agent is unsafe. Getting that wrong once costs more trust than
the launch buys.

---

## X / Twitter — main thread

**1/**
> We scanned 356 real AI agent system prompts — including shipped ones from
> Anthropic, OpenAI, Cursor and Perplexity.
>
> We checked whether each one writes down 23 basic safety controls: injection
> defense, human approval, cost caps, stop conditions.
>
> Among the 83 production prompts, median coverage was 10 out of 100.

**2/**
> This isn't a dunk. These are good prompts written by good teams.
>
> It's that the guardrails everyone assumes are in there mostly aren't — because
> nobody's checking, and there was no cheap way to check.

**3/**
> So we built one. CrewScore reads a system prompt and tells you which of the 23
> controls it never states.
>
> Offline CLI. In the browser, scoring happens locally and prompt text is never
> uploaded; anonymous allowlisted usage events may be sent unless you opt out.
>
> `pip install crewscore && crewscore scan .`

**4/**
> The number is coverage, not quality. It tells you what you haven't written
> down. It does NOT tell you your agent is safe, or that your prompt beats
> someone else's.
>
> We say that everywhere, because the opposite claim is the easy lie here.

**5/**
> How much do we mean that? Our own scale used to be broken.
>
> Through v0.1.0 a prompt that stated every control correctly scored 28/100 —
> below our lowest tier. The formula divided by rule count, so saying a thing
> once barely registered.
>
> We published the arithmetic, then fixed it.

**6/**
> The corpus study is a committed harness, not a screenshot.
>
> It fetches both corpora at pinned SHAs, runs a permutation test, and *writes
> its own report*. Every stat is emitted by code — hand-transcription is what
> got our previous study withdrawn.
>
> Cliff's δ = 0.614, p = 0.0001

**7/**
> Free, MIT, runs in your browser too (your prompt never leaves the page).
>
> crewscore.ai
> github.com/shmindmaster/crewscore

---

## X / Twitter — single-post variant

> We scanned 356 real AI agent system prompts, including shipped ones from
> Anthropic, OpenAI and Cursor.
>
> Among the 83 production prompts, median coverage of 23 basic safety controls
> — injection defense, human approval, cost caps, stop conditions — was
> **10/100**.
>
> Free tool, runs offline: crewscore.ai

---

## LinkedIn

> **We scanned 356 real AI agent prompts. Among the 83 production prompts, the
> median states 10% of basic safety controls.**
>
> That includes shipped system prompts from Anthropic, OpenAI, Cursor and
> Perplexity — teams who are very good at this.
>
> The 23 controls we checked for are unglamorous: does the prompt tell the agent
> to reject instructions embedded in user content? To stop when evidence is
> missing? To get human approval before an irreversible action? To cap spend?
>
> Mostly, they don't say. Not because the teams don't know — because prompts are
> written under deadline, reviewed by eye, and nobody had a cheap way to check
> what was missing.
>
> So we built one. CrewScore reads a system prompt and lists the controls it
> never states. It runs offline as a CLI, in CI as a GitHub Action, or in your
> browser with local scoring and no prompt upload. Anonymous allowlisted usage
> events may be sent unless you opt out. MIT licensed.
>
> **Two things it deliberately is not.**
>
> It is not a quality score. It measures whether a control is *written down* —
> not whether it is well specified, and certainly not whether the model obeys
> it. Ranking prompts or vendors by this number would be misusing it.
>
> It is not a safety certification. A perfect score means the text is present.
> That is the beginning of the work, not the end.
>
> We hold ourselves to that. Through v0.1.0 our own formula was broken: a prompt
> that stated every control correctly could only reach 28/100, because we
> divided by the number of regex patterns rather than the number of distinct
> controls. We published the arithmetic showing our scale was unusable, and then
> fixed it. The validation study documents both.
>
> 🔗 crewscore.ai · github.com/shmindmaster/crewscore

---

## Facebook

> Most AI agents are shipping without anyone checking what they were told *not*
> to do.
>
> We scanned 356 real agent prompts — including ones from Anthropic, OpenAI and
> Cursor — against 23 basic safety controls. Things like: reject instructions
> hidden in user content, stop when you're unsure, get a human to approve
> anything irreversible.
>
> Among the 83 production prompts, the median states 10 out of 100.
>
> We built a free tool that reads your prompt and tells you which ones are
> missing. Browser scoring happens locally and your prompt is never uploaded;
> anonymous allowlisted usage events may be sent unless you opt out.
>
> crewscore.ai

---

## Hacker News — Show HN

**Title:** `Show HN: CrewScore – find the safety controls your AI agent prompt never states`

**Body:**

> I kept reviewing agent system prompts by eye and kept missing the same things,
> so I wrote a checker.
>
> CrewScore reads a system prompt and reports which of 23 controls it never
> mentions — injection defense, human approval gates, cost caps, stop
> conditions, audit language. Deterministic regex, offline, no LLM, no API key.
> CLI, GitHub Action, or a browser page where the prompt never leaves the tab.
>
> The thing that surprised me: I ran it over 356 real prompts (83 shipped
> production prompts from Anthropic/OpenAI/Cursor/Perplexity, 273 GPT-Store
> ones). Production median is 10/100, GPT-Store is 0. Cliff's δ = 0.614,
> p = 0.0001, two-sided permutation test. The harness is committed, fetches
> both corpora at pinned SHAs, and writes its own report — an earlier version
> of this study was hand-written and I had to withdraw it after auditing my own
> arithmetic and finding numbers that were not just wrong but impossible (60%
> recall on n=2, a CI that contradicted its p-value). That withdrawal is in the
> repo.
>
> Two limits, stated up front because they are the whole ballgame:
>
> 1. **It measures coverage, not quality.** Whether a control is written down.
>    Not whether it is well specified, and not whether the model obeys it. It
>    cannot rank prompts.
> 2. **Regex will miss things.** The corpus run found two controls our own rules
>    were under-detecting by 6-9x, which I only caught because the harness
>    re-scans with looser probes and compares. Fixed, and the episode is in the
>    changelog.
>
> Also: through v0.1.0 the scoring formula was broken badly enough that a
> perfect prompt scored 28/100 — it divided by regex count rather than distinct
> control count, so saying something once barely registered. I published that
> arithmetic before fixing it, because a tool that grades other people's prompts
> should be willing to show its own failing grade.
>
> MIT. https://github.com/shmindmaster/crewscore

**Comment prep — the four things HN will actually say:**

- *"This is just grep."* Yes, and it says so. The value is the curated,
  cited checklist plus the anti-bloat scoring, not regex cleverness. Every rule
  and its provenance grade is printable with `crewscore rules`.
- *"Regex can't understand prompts."* Correct, which is why it reports coverage
  rather than quality, and why three dimensions ship marked known-weak.
- *"Your corpus is leaked prompts of unknown provenance."* True and stated in
  the report. Neither corpus is a random sample of anything; group membership
  is assigned by source repo, not by inspection.
- *"10/100 sounds like a made-up number."* Run the harness. One command, pinned
  SHAs, writes its own report.
- *"Static guardrails were just proven insufficient."* The impossibility
  results are about runtime robustness of guardrail *filters* against
  adversaries. CrewScore is a documentation checker — the layer NIST AI RMF
  and ISO 42001 audits actually ask about is whether controls are written
  down at all. Pair it with runtime enforcement; the README says the same.
- *"AgentLinter already does this."* There are two products named AgentLinter
  (an indie CLI and Codacy's scanner). Both lint coding-agent *config* files
  for hygiene — useful, adjacent, different artifact. Neither checks whether
  an agent *system prompt* ever states a human-approval gate, a cost ceiling,
  or a stop condition. Comparison is in `docs/comparison.md`.
- *"How will you maintain the rules as attacks evolve?"* The 23 controls track
  slow-moving governance requirements, not attack signatures — "a human must
  approve" does not rot the way an injection payload list does. The ruleset is
  versioned (`crewscore-hygiene@0.6.0`), and corpus regression tests gate every
  pattern change against measured false positives.
- *"I can paste boilerplate and score 100."* Yes — a checklist is satisfied by
  writing the thing down, and writing it down is the point. The pasted control
  now exists in a PR diff where a reviewer can judge whether it's real. The
  score cannot tell sincere from pasted; that's why we say don't rank prompts
  with it.

---

## Demo scripts

**30 seconds (terminal only).**

1. (0-5s) Blank terminal: `pip install crewscore` — cut to installed.
2. (5-15s) `crewscore test --prompt-file system-prompt.md` on a real-looking
   agent prompt → scorecard renders: **8/23 written**, first gap to review
   `A human must approve`.
3. (15-25s) Say/caption: "This prompt never says a human must approve
   anything. Most don't — median production coverage is 10/100."
4. (25-30s) `crewscore scan . --require human_gate.approval_required` → exit 2,
   red line. Caption: "Now CI fails until you write it down. Offline, no API
   key. crewscore.ai"

**60-90 seconds (terminal + browser).**

1. (0-10s) Hook: "We scanned 356 real agent system prompts. Median production
   coverage of 23 written safety controls: 10 out of 100."
2. (10-25s) Browser at crewscore.ai: paste a prompt, result renders locally —
   coverage meter, biggest gap. "Nothing is uploaded; scoring runs in the tab."
3. (25-45s) Terminal: `crewscore scan .` on a repo with `AGENTS.md` + a
   `prompts/` dir — show it classifying config vs system prompt differently
   ("config gets smells, not a governance grade — scoring your AGENTS.md
   against HIPAA language is a category error").
4. (45-60s) `crewscore fix --prompt-file ... --plan` → the missing-control
   plan; paste one suggested control in, re-run, coverage moves 8→9.
5. (60-75s) GitHub Action YAML + a PR with the sticky comment; `--require
   human_gate.approval_required` failing red, then green after the edit.
6. (75-90s) Close: "Coverage, not a safety grade. It tells you what you never
   wrote down — the rest is still your job. MIT, offline, crewscore.ai."

---

## Reddit — r/LocalLLaMA, r/MachineLearning

Lead with the data, not the tool. HN body works with the first line changed to:

> I scanned 356 real agent system prompts to see how many actually write down
> basic safety controls. Among the 83 production prompts, median coverage was
> 10/100. Method and harness below.

---

## Assets

- Social card: `docs/social-card.png` (1200×630) and `docs/github-banner.png`
  (generated by
  `scripts/make_social_card.py`)
- Demo: `docs/demo.svg`, `docs/hero-demo.gif`
- Live: [crewscore.ai](https://crewscore.ai)
