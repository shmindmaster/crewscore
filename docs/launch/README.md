# CrewScore launch kit

Pre-written public posts for soft launch (Show HN + LinkedIn same week, then X / Reddit / Dev.to).

**Brand:** CrewScore only · **Install:** `pip install crewscore` · **Site:** https://crewscore.ai  
**Repo:** https://github.com/shmindmaster/crewscore

## Assets

| File | Channel | Notes |
| --- | --- | --- |
| [show-hn.md](./show-hn.md) | Hacker News | Title + body + first comment |
| [linkedin.md](./linkedin.md) | LinkedIn | Vendor / founder path |
| [x-post.md](./x-post.md) | X / Twitter | Short + screenshot CTA |
| [reddit.md](./reddit.md) | r/LocalLLaMA, r/MachineLearning, r/ChatGPTCoding | Utility-first variants |
| [devto.md](./devto.md) | Dev.to | Longer essay draft |

## Messaging freeze (do not drift)

**Allowed**

- structural production-readiness scorecard
- offline · no API key · CI gate
- lint hygiene for system prompts
- vendor diligence checklist score

**Forbidden**

- “certified production-safe”
- “replaces red-teaming”
- any install CTA for the unrelated PyPI package named agent-guard
- claiming runtime tool-gating from prompt text alone

## Canonical share phrase

> My agent scored **47/100** on CrewScore. Structural hygiene only — not a red-team. Score yours: https://crewscore.ai · `pip install crewscore`

## Anti-promise (include in every channel)

CrewScore scores the **text** of system prompts for production-hygiene signals. It is **not** live red-teaming, runtime enforcement, or a security certification. Structural score ≠ proof the model will obey the text.

## Pre-publish checklist

- [ ] PyPI `crewscore` installs cleanly (`pip install crewscore`)
- [ ] `crewscore --version` matches published version
- [ ] Happy path: bare prompt shows low overall + 8 dimensions
- [ ] No agent-guard install CTAs anywhere in these files
- [ ] Screenshots / GIF use CrewScore branding only
- [ ] First comment on Show HN posted immediately after submission

## Suggested order

1. Show HN (title from `show-hn.md`) + first comment  
2. LinkedIn (same day or next)  
3. X with scorecard screenshot  
4. Reddit (utility tone; no spam across all three at once if rules discourage multi-post)  
5. Dev.to essay for long-tail search  
