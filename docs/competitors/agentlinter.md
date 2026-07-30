# Competitive matrix: CrewScore vs AgentLinter

Generated: `2026-07-29` · method: public-docs-and-live-crewscore-metadata; no interviews

| | CrewScore | AgentLinter |
| --- | --- | --- |
| Install | `pip install crewscore` | `npx agentlinter` |
| Repo | [shmindmaster/crewscore](https://github.com/shmindmaster/crewscore) | [seojoonkim/agentlinter](https://github.com/seojoonkim/agentlinter) |
| Stars (snapshot) | None | None |
| Offline scan | True | True |
| Fix / auto-fix | True | True |
| GitHub Action | True | True |
| Config smells path | True | (workspace lint framing) |
| Live adversarial | False | (not claimed here) |
| Certification claim | False | (not claimed here) |
| CrewScore package | `0.6.1` · `crewscore-hygiene@0.5.0` · 23 controls | — |

## Differentiation

- CrewScore separates system prompts (governance controls) from coding-agent config (smells).
- CrewScore publishes validation limits and known-poor dimensions explicitly.
- CrewScore score is equal-weight coverage of 23 controls unless corpus automation changes it.
- Neither product replaces runtime enforcement or live red-teaming.

## Honesty

This matrix is **public marketing + package metadata**, not a penetration test
of either tool. Stars and claims drift; regenerate with:

```bash
python scripts/generate_competitor_matrix.py --online
```
