"""The page must not claim more privacy than it delivers.

`analytics.js` POSTs usage events to a third party. That is defensible - the
event and property names are allowlisted, prompt text is not among them, and
person profiles are off - but it means an absolute claim like "nothing leaves
the page" is false, and it was sitting in the hero.

For a tool whose entire pitch is publishing the unflattering arithmetic about
its own number, an overclaim about privacy is the most expensive kind of
inaccuracy it could ship. These tests fail if the two ever drift apart again.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ANALYTICS = Path("analytics.js")
INDEX = Path("index.html")
SITE_JS = Path("assets/site.js")


def _index() -> str:
    return INDEX.read_text(encoding="utf-8")


def _analytics() -> str:
    return ANALYTICS.read_text(encoding="utf-8")


def _sends_data() -> bool:
    """Does the shipped page actually transmit anything?"""
    if not ANALYTICS.exists():
        return False
    if "analytics.js" not in _index():
        return False
    return bool(re.search(r"\bfetch\s*\(|sendBeacon|XMLHttpRequest", _analytics()))


# Absolute claims. Each is false the moment any byte is transmitted.
FORBIDDEN_WHEN_SENDING = [
    "nothing leaves the page",
    "nothing leaves your browser",
    "no data leaves",
    "nothing is sent",
    "we collect nothing",
    "zero telemetry",
    "no telemetry",
]


@pytest.mark.parametrize("claim", FORBIDDEN_WHEN_SENDING)
def test_page_makes_no_absolute_no_egress_claim_while_it_transmits(claim):
    if not _sends_data():
        pytest.skip("page transmits nothing; the absolute claim would be true")
    assert claim not in _index().lower(), (
        f"index.html claims {claim!r} while analytics.js transmits events"
    )


def test_transmission_is_disclosed_on_the_page():
    """Not sending is fine. Sending silently is not."""
    if not _sends_data():
        pytest.skip("nothing to disclose")
    page = _index().lower()
    assert "usage events" in page or "analytics" in page, (
        "index.html transmits events but never says so"
    )


def test_the_claim_that_survives_is_about_the_prompt():
    """The honest claim is narrower and stronger: the prompt is not uploaded."""
    page = _index().lower()
    assert "never uploaded" in page or "stays in your browser" in page or "prompt text never leaves your browser" in page


def test_prompt_text_cannot_reach_the_analytics_payload():
    """The disclosure says prompt text is excluded - that must be enforced by
    an allowlist, not by every future call site remembering."""
    if not ANALYTICS.exists():
        pytest.skip("no analytics")
    js = _analytics()
    assert "ALLOWED_PROPERTIES" in js, "no property allowlist"
    allow = re.search(
        r"ALLOWED_PROPERTIES\s*=\s*new Set\(\[(.*?)\]\)", js, re.DOTALL
    )
    assert allow, "could not read the property allowlist"
    names = set(re.findall(r'"([^"]+)"', allow.group(1)))
    # Anything that could carry free text from the prompt itself.
    for leaky in ("prompt", "text", "snippet", "content", "input", "body", "source_text"):
        assert leaky not in names, f"{leaky!r} is allowlisted into analytics"
    # The allowlist must actually gate the payload.
    assert "safeProperties" in js and "ALLOWED_PROPERTIES.has" in js


def test_analytics_never_breaks_scoring():
    """Scoring is the product; a blocked tracker must not take it down."""
    if not ANALYTICS.exists():
        pytest.skip("no analytics")
    js = _analytics()
    assert ".catch(" in js, "an unhandled rejection on a blocked request"
    # Optional-call at the call site, so a blocked or absent analytics.js
    # cannot throw into the scoring path.
    assert "window.CrewScoreAnalytics?." in SITE_JS.read_text(encoding="utf-8")


def test_last_capture_error_is_a_readable_live_status():
    """Track the last capture transport error through the exported getter."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const local = new Map([["crewscore_analytics_opt_out_v1", "0"]]);
const session = new Map();
const storage = {{
  getItem: (key) => local.get(key) || null,
  setItem: (_key, value) => local.set(_key, String(value)),
}};
const sessionStorage = {{
  getItem: (key) => session.get(key) || null,
  setItem: (key, value) => session.set(key, String(value)),
}};
const context = {{
  window: {{}},
  localStorage: storage,
  sessionStorage,
  location: {{ hostname: "crewscore.ai" }},
  crypto: {{ randomUUID: () => "test-session" }},
  fetch: () => Promise.reject(new Error("transport down")),
}};
vm.createContext(context);
vm.runInContext(source, context);
  const analytics = context.window.CrewScoreAnalytics;
(async () => {{
  await analytics.capture("cs_site_view", {{ source: "search" }});
  const firstError = analytics.lastCaptureError && analytics.lastCaptureError.message;
  await analytics.capture("cs_score", {{ source: "not-a-source", profile: "system_prompt", ruleset: "crewscore-hygiene@0.6.0", overall_bucket: 10, controls_found: 8, prompt: "SENTINEL_PROMPT" }});
  const afterInvalid = analytics.lastCaptureError && analytics.lastCaptureError.message;
  const hasGetter = !!(Object.getOwnPropertyDescriptor(context.window.CrewScoreAnalytics, "lastCaptureError") || {{}}).get;
  process.stdout.write(JSON.stringify({{
    first_error: firstError,
    after_invalid: afterInvalid,
    descriptor: hasGetter,
  }}));
}})();
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["descriptor"] is True
    assert result["first_error"] == "transport down"
    assert result["after_invalid"] == "transport down"


def test_analytics_has_a_persistent_opt_out_that_stops_capture():
    """The privacy toggle must change behavior, not merely hide a preference."""
    js = _analytics()
    page = _index()
    assert "crewscore_analytics_opt_out_v1" in js
    assert "isOptedOut()" in js
    assert "|| isOptedOut()" in js
    assert "setOptOut" in js
    assert 'id="analytics-opt-out"' in page


def test_opt_out_is_a_runtime_capture_no_op_when_node_present():
    """Exercise the production hostname branch, not just source-code shape."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const local = new Map([["crewscore_analytics_opt_out_v1", "1"]]);
const session = new Map();
const calls = [];
const storage = (store) => ({{
  getItem: (key) => store.has(key) ? store.get(key) : null,
  setItem: (key, value) => store.set(key, String(value)),
}});
const context = {{
  window: {{}},
  localStorage: storage(local),
  sessionStorage: storage(session),
  location: {{ hostname: "crewscore.ai" }},
  crypto: {{ randomUUID: () => "test-session" }},
  fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
}};
vm.createContext(context);
vm.runInContext(source, context);
const analytics = context.window.CrewScoreAnalytics;
analytics.capture("cs_check_completed", {{ prompt: "SENTINEL_PROMPT", source: "paste", profile: "system_prompt", ruleset: "crewscore-hygiene@0.6.0" }});
const whileOptedOut = calls.length;
analytics.setOptOut(false);
analytics.capture("cs_check_completed", {{ source: "paste", profile: "system_prompt", ruleset: "crewscore-hygiene@0.6.0" }});
const afterEnabled = calls.length;
const body = calls.length ? JSON.parse(calls[0][1].body) : null;
analytics.setOptOut(true);
analytics.capture("cs_check_completed", {{ source: "paste" }});
process.stdout.write(JSON.stringify({{ whileOptedOut, afterEnabled, body, finalCalls: calls.length }}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["whileOptedOut"] == 0
    assert result["afterEnabled"] == 1
    assert result["finalCalls"] == 1
    assert result["body"]["properties"]["source"] == "paste"
    assert result["body"]["properties"]["profile"] == "system_prompt"
    assert "SENTINEL_PROMPT" not in json.dumps(result["body"])


def test_runtime_capture_rejects_arbitrary_string_properties_and_unknown_events():
    """Every string-bearing property stays allowlisted and bounded."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const calls = [];
const local = new Map([["crewscore_analytics_opt_out_v1", "0"]]);
const session = new Map();
const sessionStorage = {{
  getItem: (key) => session.get(key) || null,
  setItem: (key, value) => session.set(key, String(value)),
}};
const context = {{
  window: {{}},
  localStorage: {{
    getItem: () => null,
    setItem: () => undefined,
  }},
  sessionStorage,
  location: {{ hostname: "crewscore.ai" }},
  crypto: {{ randomUUID: () => "test-session" }},
  fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
}};
vm.createContext(context);
vm.runInContext(source, context);
const analytics = context.window.CrewScoreAnalytics;
analytics.capture("cs_score", {{
  source: "https://evil.example.com",
  profile: "system_prompt",
  ruleset: "crewscore-hygiene@0.6.0",
  overall_bucket: 10,
  controls_found: 8,
  prompt: "SENTINEL_PROMPT"
}});
analytics.capture("cs_score", {{
  source: "paste",
  profile: "system_prompt",
  ruleset: "crewscore-hygiene@0.6.0",
  overall_bucket: 10,
  controls_found: 8,
  path: "chatgpt"
}});
analytics.capture("cs_share", {{ kind: "telegram" }});
analytics.capture("cs_site_view", {{ source: "search" }});
analytics.capture("cs_missing_event", {{ source: "paste" }});
process.stdout.write(JSON.stringify({{ calls: calls.length, body: calls.length ? JSON.parse(calls[0][1].body) : null }}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["calls"] == 1
    assert result["body"]["event"] == "cs_site_view"
    assert result["body"]["properties"]["source"] == "search"
    assert "SENTINEL_PROMPT" not in json.dumps(result["body"])


def test_browser_capture_labels_human_qa_without_weakening_nonproduction_suppression():
    """QA traffic uses an explicit URL flag; non-production hosts still do not send."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
function run(location) {{
  const calls = [];
  const storage = {{ getItem: () => null, setItem: () => undefined }};
  const context = {{
    window: {{}},
    document: {{ referrer: "" }},
    localStorage: storage,
    sessionStorage: storage,
    location,
    URL,
    URLSearchParams,
    crypto: {{ randomUUID: () => "test-session" }},
    fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
  }};
  vm.createContext(context);
  vm.runInContext(source, context);
  context.window.CrewScoreAnalytics.capture("cs_rules_expand", {{}});
  return calls.map((call) => JSON.parse(call[1].body));
}}
const production = run({{ hostname: "crewscore.ai", search: "" }});
const qa = run({{ hostname: "crewscore.ai", search: "?crewscore_test_traffic=true" }});
const suppressed = run({{ hostname: "localhost", search: "?crewscore_test_traffic=true" }});
process.stdout.write(JSON.stringify({{ production, qa, suppressed }}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert [body["properties"]["traffic_class"] for body in result["production"]] == [
        "production",
        "production",
    ]
    assert [body["properties"]["traffic_class"] for body in result["qa"]] == [
        "synthetic_qa",
        "synthetic_qa",
    ]
    assert result["suppressed"] == []


def test_share_url_excludes_test_traffic_without_reclassifying_the_originating_session():
    """QA links must not make recipients synthetic, but QA page capture remains labeled."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const calls = [];
const storage = {{ getItem: () => null, setItem: () => undefined }};
const location = {{
  hostname: "crewscore.ai",
  search: "?utm_source=qa&crewscore_test_traffic=true&keep=1",
  href: "https://crewscore.ai/?utm_source=qa&crewscore_test_traffic=true&keep=1#cs-result=sentinel",
}};
const context = {{
  window: {{}}, document: {{ referrer: "" }}, localStorage: storage, sessionStorage: storage,
  location, URL, URLSearchParams, crypto: {{ randomUUID: () => "test-session" }},
  fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
}};
vm.createContext(context);
vm.runInContext(source, context);
const analytics = context.window.CrewScoreAnalytics;
const shareUrl = analytics.shareUrl();
analytics.capture("cs_rules_expand", {{}});
process.stdout.write(JSON.stringify({{
  shareUrl,
  trafficClasses: calls.map((call) => JSON.parse(call[1].body).properties.traffic_class),
}}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["shareUrl"] == "https://crewscore.ai/?utm_source=qa&keep=1#cs-result=sentinel"
    assert result["trafficClasses"] == ["synthetic_qa", "synthetic_qa"]


def test_opt_out_still_blocks_capture_when_storage_is_unavailable():
    """Privacy mode cannot depend on localStorage being writable."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const calls = [];
const session = new Map();
const context = {{
  window: {{}},
  localStorage: {{
    getItem: () => {{ throw new Error("storage blocked"); }},
    setItem: () => {{ throw new Error("storage blocked"); }},
  }},
  sessionStorage: {{
    getItem: (key) => session.get(key) || null,
    setItem: (key, value) => session.set(key, String(value)),
  }},
  location: {{ hostname: "crewscore.ai" }},
  crypto: {{ randomUUID: () => "test-session" }},
  fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
}};
vm.createContext(context);
vm.runInContext(source, context);
const analytics = context.window.CrewScoreAnalytics;
const before = calls.length;
analytics.setOptOut(true);
analytics.capture("cs_check_completed", {{ source: "paste" }});
process.stdout.write(JSON.stringify({{ before, after: calls.length, optedOut: analytics.isOptedOut() }}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result == {"before": 0, "after": 0, "optedOut": True}


@pytest.mark.parametrize(
    ("referrer", "expected_source"),
    [
        ("", "direct"),
        ("https://www.google.com/search?q=private+terms", "search"),
        ("https://www.linkedin.com/feed/update/private-id", "social"),
        ("https://github.com/private-org/private-repo", "github"),
        ("https://crewscore.ai/privacy.html", "internal"),
        ("https://example.org/private/path?token=secret", "referral"),
        ("not a url", "direct"),
    ],
)
def test_site_view_reduces_referrers_to_bounded_non_pii_sources(
    referrer, expected_source
):
    """Changing the classifier to transmit a host, path, or query must fail."""
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping analytics runtime test")

    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ANALYTICS))}, "utf8");
const calls = [];
const storage = {{ getItem: () => null, setItem: () => undefined }};
const context = {{
  window: {{}},
  document: {{ referrer: {json.dumps(referrer)} }},
  localStorage: storage,
  sessionStorage: storage,
  location: {{ hostname: "crewscore.ai", href: "https://crewscore.ai/?utm_source=secret" }},
  URL,
  crypto: {{ randomUUID: () => "test-session" }},
  fetch: (...args) => {{ calls.push(args); return Promise.resolve(); }},
}};
vm.createContext(context);
vm.runInContext(source, context);
const body = JSON.parse(calls[0][1].body);
process.stdout.write(JSON.stringify(body));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    body = json.loads(proc.stdout)
    properties = body["properties"]
    assert body["event"] == "cs_site_view"
    assert properties["source"] == expected_source
    serialized = json.dumps(properties)
    if referrer:
        assert referrer not in serialized
    assert "private" not in serialized
    assert "secret" not in serialized


def test_score_tracking_emits_check_completed_before_score_for_system_prompts():
    script = SITE_JS.read_text(encoding="utf-8")
    lines = script.splitlines()
    check_idx = next(
        index for index, line in enumerate(lines) if 'track("cs_check_completed"' in line
    )
    score_idx = next(
        index for index, line in enumerate(lines) if 'track("cs_score"' in line
    )
    guard_idx = next(
        index
        for index, line in enumerate(lines)
        if "if (result.governance_applicable)" in line
    )

    assert check_idx < score_idx, "check-completed must emit before score"
    assert check_idx < guard_idx < score_idx, "check-completed should fire before the governed score branch"


def test_no_score_events_for_config_results_are_gate_enforced():
    script = SITE_JS.read_text(encoding="utf-8")
    pattern = r"function score\(source\) \{([\s\S]*?)\n  \}\n\n  function heroGapFromResult"
    match = re.search(pattern, script)
    assert match, "could not isolate score function"
    score_fn = match.group(1)
    assert "if (result.governance_applicable)" in score_fn
    assert 'track("cs_check_completed"' in score_fn
    assert 'track("cs_score"' in score_fn
    check_idx = score_fn.find('track("cs_check_completed"')
    score_idx = score_fn.find('track("cs_score"')
    guard_idx = score_fn.find("if (result.governance_applicable)")
    assert 0 <= check_idx < guard_idx < score_idx
