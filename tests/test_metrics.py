"""Privacy-safe local metrics: buckets, event store, and web/schema parity."""

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
    store = append_event({}, "cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8, "product_path": "other"})
    assert "events" in store
    assert len(store["events"]) == 1
    event = store["events"][0]
    assert event["e"] == "cs_score"
    assert "t" in event
    assert isinstance(event["t"], int)
    assert event["t"] > 0
    assert event["p"]["overall_bucket"] == 10


def test_append_event_caps_at_max_events():
    store: dict = {}
    for i in range(201):
        store = append_event(
            store,
            "cs_score",
            {
                "source": "paste",
                "profile": "system_prompt",
                "ruleset": "crewscore-hygiene@0.6.0",
                "overall_bucket": 10,
                "controls_found": 8,
            },
            max_events=200,
        )
    assert len(store["events"]) == 200
    assert store["events"][-1]["p"]["controls_found"] == 8


def test_append_event_stores_canonicalized_properties():
    store = append_event(
        {},
        "cs_score",
        {
            "source": " paste ",
            "profile": " system_prompt ",
            "ruleset": "crewscore-hygiene@0.6.0",
            "overall_bucket": 10,
            "controls_found": 8,
            "product_path": " other ",
        },
    )
    event = store["events"][0]
    assert event["p"]["source"] == "paste"
    assert event["p"]["profile"] == "system_prompt"
    assert event["p"]["product_path"] == "other"


@pytest.mark.parametrize(
    ("event", "props"),
    [
        (
            "cs_score",
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": True, "controls_found": 8},
        ),
        (
            "cs_score",
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": True},
        ),
        (
            "cs_score",
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8, "smell_count": True},
        ),
        (
            "cs_score",
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8, "delta_bucket": True},
        ),
        (
            "cs_fix_review",
            {"dims_to_fix_count": True},
        ),
        (
            "cs_fix_apply",
            {"controls_found": True},
        ),
    ],
)
def test_validate_props_rejects_bool_for_integer_fields(event, props):
    with pytest.raises(ValueError, match="integer"):
        validate_props(event, props)


@pytest.mark.parametrize(
    ("event", "seed", "bad"),
    [
        (
            "cs_score",
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8},
            {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": True, "controls_found": 8},
        ),
        (
            "cs_fix_review",
            {"dims_to_fix_count": 3},
            {"dims_to_fix_count": True},
        ),
        (
            "cs_fix_apply",
            {"controls_found": 2},
            {"controls_found": True},
        ),
    ],
)
def test_append_event_rejects_bool_in_integer_fields_without_writing(event, seed, bad):
    store = append_event({}, event, seed)
    original = list(store["events"])
    with pytest.raises(ValueError, match="integer"):
        append_event(store, event, bad)
    assert store["events"] == original


def test_validate_props_rejects_forbidden_prompt_keys():
    with pytest.raises(ValueError):
        validate_props("cs_check_completed", {"prompt": "secret", "source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0"})
    for key in ("text", "body", "system_prompt", "content", "snippet", "input", "source_text"):
        with pytest.raises(ValueError):
            validate_props("cs_score", {key: "x", "source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 0})


def test_validate_props_rejects_bad_enum_and_free_text():
    with pytest.raises(ValueError):
        validate_props("cs_score", {"source": "https://evil.site/path", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8})
    with pytest.raises(ValueError):
        validate_props("cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene", "overall_bucket": 10, "controls_found": 8})
    with pytest.raises(ValueError):
        validate_props("cs_share", {"kind": "dropbox"})


def test_validate_props_allows_safe_props():
    assert validate_props("cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 30, "controls_found": 8}) is True
    assert validate_props("cs_fix_apply", {"controls_found": 3}) is True


def test_validate_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="invalid"):
        validate_event("cs_not_a_real_event", {})


def test_validate_event_rejects_missing_required():
    with pytest.raises(ValueError, match="missing required"):
        validate_event("cs_check_completed", {"source": "paste", "profile": "system_prompt"})


def test_append_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="invalid"):
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


def test_schema_payload_is_prompt_free():
    payload = schema_payload()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert "cs_score" in payload["allowed_events"]
    assert "prompt" in payload["forbidden_prop_keys"]
    blob = str(payload).lower()
    assert "system prompt text" not in blob
