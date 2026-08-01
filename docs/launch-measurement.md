# Launch Measurement Runbook (Task 2)

This runbook is for launch telemetry only. It does not claim product-market fit, activation, or retention outcomes.

## 1) Funnel map and event contract

We measure the flow from landing to share/feedback using bounded event names and bounded values.

Every event can also carry optional `traffic_class`: `production` (the browser
default) or `synthetic_qa`. The production browser assigns `synthetic_qa` only
when the URL contains `crewscore_test_traffic=true`; that flag does not enable
capture from a non-production hostname.

### Step: visit
- Event: `cs_site_view`
- Required property: `source`
- Allowed values: `direct`, `internal`, `github`, `search`, `social`, `referral`
- Purpose: capture how people reached the page without raw referrer data.
- Denominator: all sessions that emitted `cs_site_view`.

### Step: check
- Event: `cs_check_completed`
- Required properties: `source`, `profile`, `ruleset`
- Allowed values:
  - `source`: bounded source enum + `paste`, `file_upload`, `github_import`, `example`, `demo`, `profile_change`, `mobile`, `fix_apply`
  - `profile`: `system_prompt`, `coding_agent_config`
  - `ruleset`: `crewscore-hygiene@x.y.z`
- Purpose: confirm that a live check ran in-browser.
- Denominator: sessions with a prior `cs_site_view`.

### Step: score
- Event: `cs_score`
- Required properties: `source`, `profile`, `ruleset`, `overall_bucket`, `controls_found`
- Optional properties: `product_path`, `smell_count`, `delta_bucket`
- Allowed:
  - `product_path`: `chatgpt`, `claude`, `cursor`, `other`
  - `overall_bucket`, `delta_bucket`: `0|10|20|30|40|50|60|70|80|90|100`
  - `controls_found`, `smell_count`: integer `0..23`
- Purpose: capture written-control outcome from the scorer.
- Denominator: prior `cs_check_completed` sessions.

### Step: fix review
- Event: `cs_fix_review`
- Required property: `dims_to_fix_count`
- Allowed: integer `0..23`
- Purpose: indicates the user opened the fix-review flow.
- Denominator: `cs_score` sessions.

### Step: fix apply
- Event: `cs_fix_apply`
- Required property: `controls_found`
- Allowed: integer `0..23`
- Purpose: user applied at least one suggested wording.
- Denominator: `cs_fix_review` sessions.

### Step: share / feedback
- Event: `cs_share`
- Required property: `kind`
- Allowed values: `copy_result`, `copy_share_text`, `copy_team`, `copy_badge`, `native`, `x`, `linkedin`, `facebook`, `reddit`, `svg_linkedin`, `svg_x`, `svg_facebook`, `svg_reddit`, `svg_square`, `svg_badge`, `png_linkedin`, `png_x`, `png_facebook`, `png_square`, `png_badge`
- Purpose: capture share intent.
- Denominator: sessions with at least one scored result.

- Event: `cs_product_path`
- Required property: `path`
- Allowed values: `chatgpt`, `claude`, `cursor`, `other`, `feedback`
- Purpose: capture chosen path segment and explicit feedback path.
- Denominator: all sessions.

## 2) Referral and product-path constraints

- Referral is reduced to bounded values only. Raw URL host/path/query is never sent.
- Product path values are bounded with default `other`.
- Raw user-facing strings are never copied into analytics payloads.

## 3) Privacy and data minimization

- Prompt text and free-form prompt content are not allowed in analytics payloads.
- All sendable string properties are bounded enumerations and max length checks.
- Numeric properties are bounded.
- `traffic_class` is a bounded, optional classification for production versus
  explicitly flagged human QA traffic; it is not derived from prompt content.
- Every PostHog request adds fixed transport properties `$geoip_disable: true`
  and `$process_person_profile: false`. Callers cannot override either value;
  neither property admits user or prompt content.
- Opt-out (`crewscore_analytics_opt_out_v1`) and offline states never block scoring.
- Unknown, missing, or extra properties are rejected before any network body is built.

## 4) Review cadence

- 24-hour review: schema health, conversion per funnel stage, and any regression versus yesterday.
- 7-day review: trend for funnel stage rates and referral/product-path mix.

## 5) Minimum sample caveat

- If the denominator is too small, do not publish directional percentages.
- For `visit->check` and `check->score` transitions, use only raw counts when active sessions are low (recommended guard: <30 in 24h or <150 in 7 days).

## 6) Event safety precondition before any public claim

Before publishing or changing copy:
1. Re-run schema parity tests.
2. Re-run fixture-to-svg generator determinism checks.
3. Re-run focused analytics claim tests for prompt text never reaching network bodies.
4. Re-run focused browser tests after any instrumentation change.

## 7) Telemetry vs activation/adoption/PMF

- This telemetry is usage telemetry.
- `cs_score` and `cs_fix_apply` are usage outcomes, not activation.
- Session-level repeated checks are the most precise behavioral signal available from first-party telemetry.
- PMF, retention, and willingness-to-pay are separate studies and are not inferred from these events.
