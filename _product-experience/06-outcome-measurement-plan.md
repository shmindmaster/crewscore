# CrewScore — Outcome measurement plan

## Decision this plan supports

Did the preflight web experience improve **successful structural pre-gates** (score → understand → act → export) without increasing overclaim/trust failure?

## Population & journey

- **Population:** Anonymous visitors to crewscore.ai + optional CLI users (separate)  
- **Journey boundary:** First paint → first score → optional fix apply → optional share/CI copy  
- **Baseline:** Pre-redesign qualitative (manual Playwright + audit F1–F9)  
- **Comparison:** Post-deploy week-over-week funnel (if analytics enabled)

## Metrics (balanced)

| Outcome | Metric | Guardrail |
| --- | --- | --- |
| Activation | % sessions with ≥1 score | Bounce without interaction |
| Understanding | % expand "top gaps" or dim row | Time-to-score only |
| Controlled fix | % fix_plan_shown → fix_applied | fix_applied without plan (should be ~0) |
| Export | % share_or_download_or_ci_copy | Share without score (should be 0) |
| Trust | Qualitative: can restate "not red-team" | Support/issue reports of overclaim |
| Privacy | Zero prompt text in analytics | Any payload containing prompt body = fail |

## Event semantics (privacy-safe)

No prompt text, no URLs of private gists content, no PII.

| Event | Properties |
| --- | --- |
| `cs_score` | `source`: template\|paste\|url; `overall_bucket`: 0\|1-49\|50-69\|70-89\|90-100; `ruleset` |
| `cs_fix_plan` | `dims_to_fix_count` |
| `cs_fix_apply` | `delta_bucket` |
| `cs_fix_cancel` | — |
| `cs_export` | `kind`: share_text\|share_img\|download_prompt\|ci_copy |
| `cs_rules_expand` | — |
| `cs_vendor_open` | — |

**Implementation default for OSS launch:** localStorage counters only (`crewscore_metrics_v1`) + optional `console.debug` — no third-party by default. Document how to wire Plausible/Umami later with same events.

**Schema authority:** Python module `crewscore/metrics.py` (`bucket_score`, `append_event`, `validate_props`) is the testable source of truth for event buckets and forbidden prop keys; web localStorage must keep matching event names/buckets.

## Decision thresholds (pre-commit)

| Signal | Green | Yellow | Red |
| --- | --- | --- | --- |
| Score rate (engaged sessions) | ≥40% | 20–40% | <20% |
| Fix apply / plan ratio | 30–80% | <30% or >90% | plan never shown |
| Export after score | ≥15% | 5–15% | <5% |
| Trust issues (manual) | 0 severe | wording nits | "certification" complaints |

## Qualitative

- 5 builder think-alouds: "what does this score mean?"  
- Show HN first-comment monitoring for black-box / overclaim language  

## Limitations

No production analytics currently; local counters only until owner enables privacy-respecting host.
