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

import re
from pathlib import Path

import pytest

ANALYTICS = Path("analytics.js")
INDEX = Path("index.html")


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
    assert "never uploaded" in page or "stays in your browser" in page


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
    assert "window.CrewScoreAnalytics?." in _index()
