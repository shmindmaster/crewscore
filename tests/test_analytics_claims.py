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
analytics.capture("cs_check_completed", {{ prompt: "SENTINEL_PROMPT", source: "paste" }});
const whileOptedOut = calls.length;
analytics.setOptOut(false);
analytics.capture("cs_check_completed", {{ prompt: "SENTINEL_PROMPT", source: "paste" }});
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
    assert "SENTINEL_PROMPT" not in json.dumps(result["body"])


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
    assert result == {"before": 1, "after": 1, "optedOut": True}


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
