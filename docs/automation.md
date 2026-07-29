# Automation and merge gates

CrewScore uses **machine gates**, not human code review, as the default path
from PR to `main`. Humans decide product direction and irreversible public
actions; CI decides whether a change may land.

## Default path (no human review required)

```
agent/maintainer opens PR (same-repo, owner)
        │
        ▼
 required checks (branch protection on main)
   • test (3.11)
   • test (3.12)
   • test (3.13)
   • browser tests
   • selftest
        │
        ▼
 auto-merge (squash) when checks are green
        │
        ▼
 main → Pages deploy / next release tag
```

| Control | Mechanism |
| --- | --- |
| Correctness | pytest matrix + browser + Action self-test |
| Trust boundary | Self-hosted jobs only run owner same-repo PRs |
| Landing | Repo `allow_auto_merge` + workflow `auto-merge-owner-prs.yml` |
| History | Squash merge; delete head branch after merge |
| Bypass human review | Intentional: `required_pull_request_reviews` is **off** |

### Opt out of auto-merge

Add the label **`no-automerge`** to a PR. Checks still run; merge becomes
manual (`gh pr merge` when green).

## What still needs a human decision

These are **not** merge blockers for ordinary engineering PRs. They are
product/release ownership decisions:

| Decision | Why a human |
| --- | --- |
| Public Show HN / social posts | Irreversible external messaging |
| Gate 0 strategy (credibility vs acquisition-shaped) | Business outcome |
| Scoring formula / ruleset arithmetic change | Changes every consumer's numbers |
| PyPI release cut (version tag) | Publishing is one-way; tag must match package |
| Secrets / trusted publisher setup | Account-level |

Release automation already exists: push tag `vX.Y.Z` → `release.yml` tests,
builds, and publishes via OIDC. The human step is **choosing** to tag, not
re-reviewing every file.

## Scoring changes: higher bar (still machine-enforced)

When a PR changes `structural_analysis.py`, `CONCEPTS`, score arithmetic, or
`RULESET_ID`, required checks still include the full suite. Additionally:

1. `python scripts/export_web_engine.py` must be committed (parity tests fail otherwise)
2. CHANGELOG must note scoring impact
3. Prefer a ruleset id / version bump in the same PR

Optional future hardening (not required today): a path-filter job that fails
if scoring files change without a `RULESET_ID` bump.

## Linear / agent workflow

| Old language | New language |
| --- | --- |
| "Human review of PR" | "CI green → auto-merge" |
| "Awaiting review" | "In Review only if labeled `no-automerge` or blocked on product decision" |
| Release "after review" | Tag after CI green on `main` (or release PR with auto-merge) |

Agents should:

1. Open a PR from a feature branch
2. Wait for required checks (or enable auto-merge immediately)
3. Not block on a person reading the diff for routine work
4. Only escalate when a **human decision** row above applies

## Security notes

- Fork PRs never get self-hosted runners (existing workflow `if:` guards).
- Auto-merge only enables for `repository_owner` + same-repo head.
- Branch protection enforces status checks even for admins (`enforce_admins`).
- Do not store long-lived PyPI tokens; release uses trusted publishing.

## Related

- [Development](development.md)
- [GitHub Action](github-action.md)
- [Cleanup inventory](cleanup-and-completion.md)
