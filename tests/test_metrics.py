"""Privacy-safe local metrics: buckets, event store, no prompt capture."""

import pytest

from crewscore.metrics import append_event, bucket_score, validate_props


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
        store = append_event(store, "cs_score", {"overall_bucket": "0", "i": i}, max_events=200)
    assert len(store["events"]) == 200
    # keep the most recent events
    assert store["events"][-1]["p"]["i"] == 200


def test_validate_props_rejects_forbidden_prompt_keys():
    result_or_exc = None
    try:
        result_or_exc = validate_props({"prompt": "secret"})
    except ValueError as exc:
        result_or_exc = exc
    assert isinstance(result_or_exc, ValueError) or result_or_exc is False

    for key in ("text", "body", "system_prompt", "content", "PROMPT", "System_Prompt"):
        try:
            out = validate_props({key: "x"})
        except ValueError:
            continue
        assert out is False, f"expected reject for key {key!r}"


def test_validate_props_allows_safe_props():
    out = validate_props({"overall_bucket": "0"})
    assert out is True or out is None
