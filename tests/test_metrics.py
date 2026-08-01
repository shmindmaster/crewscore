"""Privacy-safe local metrics: buckets, event store, and web/schema parity."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from crewscore.metrics import (
    ALLOWED_EVENTS,
    ALLOWED_PROPERTIES,
    CAPTURE_FORBIDDEN_PROP_KEYS,
    CAPTURE_SCHEMA_VERSION,
    FORBIDDEN_PROP_KEYS,
    SCHEMA_VERSION,
    append_event,
    bucket_score,
    capture_schema_payload,
    parse_analytics_allowlists,
    schema_payload,
    validate_capture_event,
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


def test_append_event_stores_unmodified_properties():
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
    assert event["p"]["source"] == " paste "
    assert event["p"]["profile"] == " system_prompt "
    assert event["p"]["product_path"] == " other "


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
def test_validate_event_rejects_bool_for_integer_fields(event, props):
    with pytest.raises(ValueError, match="integer"):
        validate_capture_event(event, props)


def test_append_event_preserves_extra_properties_and_does_not_strip():
    store = append_event(
        {},
        "cs_score",
        {
            "source": "paste",
            "profile": " system_prompt ",
            "ruleset": "crewscore-hygiene@0.6.0",
            "overall_bucket": 10,
            "controls_found": 8,
            "local_note": "allowed",
            "product_path": "other",
        },
    )
    event = store["events"][0]
    assert event["p"]["profile"] == " system_prompt "
    assert event["p"]["local_note"] == "allowed"


def test_append_event_rejects_forbidden_property_without_writing():
    store = append_event({}, "cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8})
    original = list(store["events"])
    with pytest.raises(ValueError, match="must not include prompt text"):
        append_event(store, "cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8, "prompt": "x"})
    assert store["events"] == original


def test_validate_event_rejects_strict_schema_extras():
    with pytest.raises(ValueError, match="unexpected property"):
        validate_capture_event("cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8, "local_note": "x"})


def test_append_event_accepts_strict_schema_extras_as_safe_local_props():
    store = append_event(
        {},
        "cs_score",
        {
            "source": "paste",
            "profile": "system_prompt",
            "ruleset": "crewscore-hygiene@0.6.0",
            "overall_bucket": 10,
            "controls_found": 8,
            "local_note": "x",
        },
    )
    event = store["events"][0]
    assert event["p"]["local_note"] == "x"


def test_validate_props_rejects_forbidden_prompt_keys():
    with pytest.raises(ValueError):
        validate_props({"prompt": "secret", "source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0"})
    with pytest.raises(ValueError):
        validate_props({"PROMPT": "secret", "source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0"})
    for key in ("text", "body", "system_prompt", "content"):
        with pytest.raises(ValueError):
            validate_props({key: "x", "source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 0})


def test_capture_contract_rejects_expanded_content_keys_without_breaking_069_public_api():
    for key in ("snippet", "input", "source_text"):
        assert validate_props({key: "legacy-safe"}) is True
        assert validate_event("cs_score", {key: "legacy-safe"}) is True
        append_event({}, "cs_score", {key: "legacy-safe"})
        with pytest.raises(ValueError, match="forbidden prompt-content"):
            validate_capture_event(
                "cs_score",
                {
                    "source": "paste",
                    "profile": "system_prompt",
                    "ruleset": "crewscore-hygiene@0.6.0",
                    "overall_bucket": 10,
                    "controls_found": 8,
                    key: "blocked-before-network",
                },
            )


def test_validate_props_rejects_bad_enum_and_free_text():
    with pytest.raises(ValueError):
        validate_capture_event("cs_score", {"source": "https://evil.site/path", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 10, "controls_found": 8})
    with pytest.raises(ValueError):
        validate_capture_event("cs_score", {"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene", "overall_bucket": 10, "controls_found": 8})
    with pytest.raises(ValueError):
        validate_capture_event("cs_share", {"kind": "dropbox"})


def test_validate_props_allows_safe_props():
    assert validate_props({"source": "paste", "profile": "system_prompt", "ruleset": "crewscore-hygiene@0.6.0", "overall_bucket": 30, "controls_found": 8}) is True
    assert validate_props({"controls_found": 3}) is True


def test_validate_event_rejects_unknown_event():
    with pytest.raises(ValueError, match="unknown metrics event"):
        validate_event("cs_not_a_real_event", {})


def test_validate_event_rejects_missing_required():
    with pytest.raises(ValueError, match="missing required"):
        validate_capture_event("cs_check_completed", {"source": "paste", "profile": "system_prompt"})


@pytest.mark.parametrize("traffic_class", ("production", "synthetic_qa"))
def test_capture_contract_accepts_optional_bounded_traffic_class(traffic_class):
    assert validate_capture_event(
        "cs_rules_expand", {"traffic_class": traffic_class}
    ) is True


def test_capture_contract_rejects_unrecognized_traffic_class():
    with pytest.raises(ValueError, match="unrecognized enum"):
        validate_capture_event("cs_rules_expand", {"traffic_class": "staging"})


def test_capture_contract_exposes_optional_traffic_class_for_every_event():
    payload = capture_schema_payload()
    for event in payload["event_schemas"].values():
        assert event["properties"]["traffic_class"] == {
            "type": "string",
            "enum": ["production", "synthetic_qa"],
            "max_length": 16,
        }


def test_validate_event_preserves_published_069_sparse_safe_contract():
    assert validate_event("cs_score", {"source": "paste"}) is True
    assert validate_event("cs_score", {"overall_bucket": True, "local_note": "kept locally"}) is True
    with pytest.raises(ValueError, match="must not include prompt text"):
        validate_event("cs_score", {"prompt": "must never be stored"})


def test_validate_props_accepts_raw_legacy_payload():
    payload = {
        "source": "paste",
        "profile": "system_prompt",
        "ruleset": "crewscore-hygiene@0.6.0",
        "overall_bucket": 30,
        "controls_found": 8,
    }
    assert validate_props(payload) is True


def test_validate_props_preserves_published_069_keyword_parameter():
    assert validate_props(props={"source": "paste"}) is True


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
    assert CAPTURE_SCHEMA_VERSION in js


def _analytics_schema_payload_from_js() -> dict[str, Any]:
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping deep JS schema parity")
    script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync({json.dumps(str(ROOT / "analytics.js"))}, "utf8");
const context = {{ window: {{}} }};
vm.createContext(context);
vm.runInContext(source, context);
process.stdout.write(JSON.stringify(context.window.CrewScoreAnalytics.schemaPayload()));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_analytics_js_schema_payload_matches_python_contract():
    payload_python = capture_schema_payload()
    payload_js = _analytics_schema_payload_from_js()

    assert payload_js["schema_version"] == payload_python["schema_version"] == CAPTURE_SCHEMA_VERSION
    assert sorted(payload_js["allowed_events"]) == sorted(payload_python["allowed_events"])
    assert sorted(payload_js["allowed_properties"]) == sorted(payload_python["allowed_properties"])
    assert set(payload_js["forbidden_prop_keys"]) == set(payload_python["forbidden_prop_keys"])
    assert payload_js["prompt_text"] == payload_python["prompt_text"]
    assert payload_js["score_buckets"] == payload_python["score_buckets"]
    assert payload_js["optional_properties"] == payload_python["optional_properties"]

    py_events = payload_python["event_schemas"]
    js_events = payload_js["event_schemas"]
    assert set(js_events) == set(py_events)

    for event in sorted(py_events):
        js_schema = js_events[event]
        py_schema = py_events[event]
        assert js_schema["required"] == py_schema["required"]
        assert set(js_schema["properties"]) == set(py_schema["properties"])
        for name in py_schema["properties"]:
            js_prop = js_schema["properties"][name]
            py_prop = py_schema["properties"][name]
            assert js_prop["type"] == py_prop["type"]
            assert js_prop.get("min") == py_prop.get("min")
            assert js_prop.get("max") == py_prop.get("max")
            assert js_prop.get("max_length") == py_prop.get("max_length")
            assert js_prop.get("enum") == py_prop.get("enum")
            assert js_prop.get("pattern") == py_prop.get("pattern")


def test_schema_payload_is_prompt_free():
    payload = schema_payload()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert SCHEMA_VERSION == "2026-07-30"
    assert "cs_score" in payload["allowed_events"]
    assert "prompt" in payload["forbidden_prop_keys"]
    assert set(payload["forbidden_prop_keys"]) == set(FORBIDDEN_PROP_KEYS)
    assert set(CAPTURE_FORBIDDEN_PROP_KEYS) == set(FORBIDDEN_PROP_KEYS) | {"snippet", "input", "source_text"}
    assert payload["score_buckets"] == ["0", "1-49", "50-69", "70-89", "90-100"]
    assert payload["network"] == "web client only; Python core never sends metrics"
    blob = str(payload).lower()
    assert "system prompt text" not in blob
