# Project-wide human-gate inventory (CrewScore)

**Authority date:** 2026-07-30  
**Policy:** eliminate human process theater; machine gates decide landings; interviews canceled.

Sources audited: GitHub repo (code, workflows, docs), Linear project `[Pendoah] Marketplace Launch 2026`, Notion (workspace search for CrewScore / review / PMF).

---

## Decision framework (research-backed)

| Pattern | Source insight | CrewScore application |
| --- | --- | --- |
| Required status checks + auto-merge | GitHub: auto-merge after requirements; automate checks instead of mandatory human review | Branch protection: pytest matrix, browser, selftest; no required reviews; owner auto-merge |
| OSS PMF without interviews | Proxy metrics: stars, downloads, issues, CI consumers; continuous automated checks | `scripts/collect_product_signals.py`; corpus validation; FP/FN issue templates |
| Competitive research without workshops | Public docs + package metadata, reproducible scripts | `scripts/generate_competitor_matrix.py` |
| Distribution without founder ops | Generated channel packs; optional APIs | `scripts/generate_dist_pack.py` → `docs/dist-pack/` |
| Strategy without meetings | Lock defaults in repo policy docs | Gate 0 + category vocabulary locked in Linear + `docs/automation.md` |

---

## Complete inventory

### A. Engineering / deployment (repo)

| Item | Was human? | Disposition | Automation |
| --- | --- | --- | --- |
| PR code review before merge | Process only | **Removed** | Required CI + squash auto-merge |
| Branch protection reviews | — | **Off** | Status checks only |
| Release version tag | Manual | **Automated** | `scripts/cut_release.py --push`; Actions `Cut release tag`; `v0.6.1` cut |
| PyPI publish | Manual token | **Automated** | OIDC trusted publisher on tag |
| GitHub Release notes | Manual | **Automated** | release.yml from CHANGELOG |
| Pages deploy | — | **Automated** | GitHub Pages on main |
| Fork PR self-hosted CI | Trust decision | **Automated skip** | Workflow `if:` owner same-repo only |
| `init` overwrite safety | Operator | **Machine** | Refuse without `--force` |
| Web engine staleness | Manual catch | **CI fail** | export parity tests |
| Packaging contract | Manual | **CI** | `test_packaging_contract` |
| Claim / honesty copy | Manual review | **CI** | published numbers + credibility tests |
| Scoring governance meeting | Human | **Policy** | CHANGELOG + ruleset + tests in PR |

### B. Product validation / research

| Item | Disposition | Replacement |
| --- | --- | --- |
| PMF interviews (12) + concierge (20) | **Canceled** SH-2366 | Product signals JSON + corpus + GitHub/PyPI public APIs |
| Gate 0 strategy workshop | **Done/locked** SH-2382 | Community-credibility default |
| Category naming workshop | **Done/locked** SH-2388 | Configuration smells + written controls |
| Ecosystem strategy essay | **Canceled** SH-2385 | Ship integrations with CI |
| AgentLinter research workshop | **Automated** SH-2384 | Competitor matrix script |
| Dimension reweight committee | **Automated path** SH-2386 | Corpus-driven validity job (equal weights until evidence) |
| Live adversarial product for launch | **Deferred** SH-2344 | `export-eval` handoff only |

### C. Distribution / launch

| Item | Disposition | Replacement |
| --- | --- | --- |
| Manual Show HN copy shop | **Scripted** | `generate_dist_pack.py` |
| Manual social posts as process gate | **Not a gate** | Drafts staged; optional API later |
| Launch content kit | **Done** (assets) | Dist pack regenerates from truth |

### D. Product UX (not maintainer process)

| Item | Note |
| --- | --- |
| Browser “review suggested guardrails” | End-user selects templates — keep |
| Scoring `human_gate.*` controls | Detect written approval language — keep |
| Security advisory private report | Occasional human triage of exploits — unavoidable residual; not a backlog “interview” |

### E. Notion

| Finding | Action |
| --- | --- |
| No CrewScore-owned review/merge policy page | **None required** — ignore other products’ interview/review gates |
| Portfolio runbook / Verigence / Sabhi human gates | **Out of scope** for CrewScore |

### F. Linear open automation work (agent-executable)

| Issue | Status | Automation artifact |
| --- | --- | --- |
| SH-2410 release 0.6.1 | **In progress / cutting** | Tag `v0.6.1` pushed |
| SH-2379 dist pack | Largely **implemented** | `docs/dist-pack/` |
| SH-2384 competitor matrix | **Implementing** | `docs/competitors/` |
| SH-2386 dimension validity | Todo | Corpus report job (next) |
| SH-2344 adversarial | Backlog post-traction | export-eval only |

---

## Explicitly removed requirements

1. Human PR review as merge gate  
2. PMF interview / concierge sprint  
3. Gate 0 / category / ecosystem human workshops  
4. “Await review” language as process for agents  
5. Manual release cut after person reads the diff  

## Residual non-automatable (accepted)

| Residual | Why kept |
| --- | --- |
| One-time PyPI trusted-publisher bind (if missing) | Account browser OAuth |
| Optional third-party social API secrets | Credential creation |
| Real security exploit triage | Legal/safety judgment |
| HN has no official public post API | Draft pack is max clean automation |

---

## Commands (agent playbook)

```bash
# land code
# → open PR; auto-merge when checks green

# product signals (no interviews)
python scripts/collect_product_signals.py --online

# competitive matrix
python scripts/generate_competitor_matrix.py --online

# channel drafts
python scripts/generate_dist_pack.py

# release
python scripts/cut_release.py --push
```

See also [automation.md](automation.md).
