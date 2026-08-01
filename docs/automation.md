# Automation and merge gates

CrewScore optimizes for **agents and machines**, not human process theater.
CI decides whether code lands. Scripts decide release tags and channel drafts.
Humans are not a required step for merge, interviews, or strategy workshops.

## Default engineering path (no human review)

```
agent opens owner same-repo PR
        │
        ▼
 required checks on main
   • test (3.11) / (3.12) / (3.13)
   • browser tests
   • selftest
        │
        ▼
 squash auto-merge (auto-merge-owner-prs.yml)
        │
        ▼
 main → Pages; optional tag cut → PyPI (release.yml OIDC)
```

| Control | Mechanism |
| --- | --- |
| Correctness | pytest matrix + browser + Action self-test |
| Trust boundary | Self-hosted jobs only for owner same-repo PRs |
| Landing | `allow_auto_merge` + `auto-merge-owner-prs.yml` |
| Reviews | **Not required** (`required_pull_request_reviews` off) |
| Opt-out | Label PR `no-automerge` |

## Former "human gates" → automation status

| Former human item | Status | Automation |
| --- | --- | --- |
| PR code review | **Removed** | Required checks + auto-merge |
| PMF interviews (12 + 20) | **Canceled** (Linear SH-2366) | Stars, downloads, Action runs, FP/FN issues, corpus metrics |
| Gate 0 strategy meeting | **Locked default** (SH-2382 Done) | Community-credibility / checklist honesty in docs |
| Category naming workshop | **Locked default** (SH-2388 Done) | "Configuration smells" + written-control checklist |
| Ecosystem strategy essay | **Canceled** (SH-2385) | Ship integrations with CI only |
| Manual Show HN copy shop | **Scripted drafts** | `python scripts/generate_dist_pack.py` |
| Manual release tag after "review" | **Scripted** | `python scripts/cut_release.py --push` or Actions `Cut release tag` |
| Dimension reweight committee | **Corpus job** (SH-2386) | Automated hit-rate / separation report proposes change |
| AgentLinter research workshop | **Scrape matrix** (SH-2384) | Scripted public docs matrix |
| Live adversarial product | **Deferred** (SH-2344) | `export-eval` handoff only; no in-product live attacks |

## Release automation

1. Bump `pyproject.toml` + `crewscore/__init__.py` + CHANGELOG section `## [X.Y.Z]`.
2. Land via auto-merge PR (or push through machine gates).
3. Cut tag:

```bash
python scripts/cut_release.py          # dry-run
python scripts/cut_release.py --push   # annotated tag + push → release.yml
```

Or: Actions → **Cut release tag** → `push: true` on `main`.

Tag push runs full multi-OS verify + PyPI trusted publishing + GitHub Release
notes from CHANGELOG. **No long-lived PyPI token.**

Release-time verification (not performed from a release-candidate branch):

1. Confirm the annotated `vX.Y.Z` tag peels to the exact green `main` SHA.
2. Confirm PyPI wheel/sdist metadata and the GitHub Release target that SHA.
3. Confirm the release workflow moved floating Action tag `v2` to the same SHA.
4. Regenerate the distribution pack from that checkout and retain its
   `manifest.json` plus `checksums.txt` as launch evidence.

One-time (already documented in `release.yml`): PyPI trusted publisher binding
for `shmindmaster/crewscore` / `release.yml` / environment `pypi`.

## Distribution pack (no interviews)

```bash
python scripts/generate_dist_pack.py
# → _production/launch/dist-pack/{show-hn-title.txt,show-hn-first-comment.md,x-post.txt,linkedin-post.md,community-post.md,answer-bank.md,manifest.json,checksums.txt}
# (gitignored — channel drafts are working material, never published docs)
# Source of truth: docs/launch-copy.json.
```

Posts are **drafts** by default (`posts_automatically: false`). Optional future:
X/GitHub Discussion APIs when secrets exist. HN has no official post API —
draft paste or third-party tools remain optional, not a process gate.

## Product / CI gates (machine, not maintainer review)

- `--require` / baseline regression / `--max-smells` / Action SARIF
- Browser "review suggested guardrails" = end-user UX
- Scoring control `human_gate.*` = text pattern, not process

## Scoring-file changes

Still land via the same auto-merge path, but must include:

1. Regenerated `score-engine.js` (parity tests)
2. CHANGELOG scoring note
3. Prefer `RULESET_ID` bump when arithmetic changes

## Agent rules of engagement

1. Do **not** wait for a person to read a PR.
2. Do **not** open interview / workshop / "human distribution" tickets.
3. Prefer scripts + CI evidence over meetings.
4. Escalate only for account-level secrets the agent cannot create (e.g. first-time PyPI OIDC bind, if missing).

## Related

- [Development](development.md)
- [GitHub Action](github-action.md)

Internal working material (audit inventories, competitor matrix, product
signals, channel drafts) lives under the gitignored `_production/` directory —
it is maintainer working data, not published documentation.
