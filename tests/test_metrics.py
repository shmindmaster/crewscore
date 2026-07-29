"""Privacy-safe local metrics: buckets, event store, web allowlist parity."""

from __future__ import annotations

from pathlib import Path

import pytest

from crewscore.metrics import (
    ALLOWED_EVENTS,
    ALLOWED_PROPERTIES,
    SCHEMA_VERSION,
    append_event,
    bucket_score,
    parse_analytics_allowlists,
    schema_payload,
    validate_event,
    validate_props,
)

ROOT = Path(__file__).resolve().parents[1]


def test_bucket_score_boundaries():
    assert bucket_score(0) == "0"
    assert bucket_score(25) == "1-49"
    assert bucket_score(50) == "50-69"
    assert bucket_score(70) == "70-89"
    assert bucket_score(90) == "90-100"
    assert bucket_score(100) == "90-100"


def test_append_event_adds_timestamped_entry():
    store = append_event({}, "cs_score", {"overall_bucket": "0", "source": "paste"})
    assert "events" in store
    assert len(store["events"]) == 1
    event = store["events"][0]
    assert event["e"] == "cs_score"
    assert "t" in event
    assert isinstance(event["t"], (int, float))
    assert event["t"] > 0
    assert event["p"] == {"overall_bucket": "0", "source": "paste"}


def test_append_event_caps_at_max_events():
    store: dict = {}
    for i in range(201):
        store = append_event(
            store, "cs_score", {"overall_bucket": "0", "i": i}, max_events=200
        )
    assert len(store["events"]) == 200
    # keep the most recent events
    assert store["events"][-1]["p"]["i"] == 200


def test_validate_props_rejects_forbidden_prompt_keys():
    with pytest.raises(ValueError):
        validate_props({"prompt": "secret"})

    for key in ("text", "body", "system_prompt", "content", "PROMPT", "System_Prompt"):
        with pytest.raises(ValueError):
            validate_props({key: "x"})


def test_validate_props_allows_safe_props():
    assert validate_props({"overall_bucket": "0"}) is True


def test_validate_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="unknown metrics event"):
        validate_event("cs_not_a_real_event")


def test_append_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="unknown metrics event"):
        append_event({}, "cs_not_a_real_event", {})


def test_analytics_js_allowlists_match_python_schema():
    """Python metrics module is the schema authority; analytics.js must match."""
    js = (ROOT / "analytics.js").read_text(encoding="utf-8")
    parsed = parse_analytics_allowlists(js)
    assert "ALLOWED_EVENTS" in parsed
    assert "ALLOWED_PROPERTIES" in parsed
    assert parsed["ALLOWED_EVENTS"] == ALLOWED_EVENTS
    assert parsed["ALLOWED_PROPERTIES"] == ALLOWED_PROPERTIES
    assert SCHEMA_VERSION in js
    assert f'schema_version: "{SCHEMA_VERSION}"' in js or (
        f"schema_version: '{SCHEMA_VERSION}'" in js
    )


def test_schema_payload_is_prompt_free():
    payload = schema_payload()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert "cs_score" in payload["allowed_events"]
    assert "prompt" in payload["forbidden_prop_keys"]
    blob = str(payload).lower()
    assert "system prompt text" not in blob
