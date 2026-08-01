"""Privacy-safe metrics schema (no network from Python, never store prompt text)."""

from __future__ import annotations

import re
import time
from typing import Any

# Exact public 0.6.9 contract. Browser capture has a separately versioned schema.
SCHEMA_VERSION = "2026-07-30"
CAPTURE_SCHEMA_VERSION = "2026-07-31"

# Maximum allowed control counts per control map for this branch.
CONTROL_MAX = 23

BUCKETS = (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
SCORE_BUCKETS = ("0", "1-49", "50-69", "70-89", "90-100")
RULESET_RE = re.compile(r"^crewscore-hygiene@\d+\.\d+\.\d+$")

SOURCE_ENUM = frozenset(
    {
        "direct",
        "internal",
        "github",
        "search",
        "social",
        "referral",
        "paste",
        "file_upload",
        "github_import",
        "example",
        "demo",
        "profile_change",
        "mobile",
        "fix_apply",
    }
)

PROFILE_ENUM = frozenset({"system_prompt", "coding_agent_config"})
MODE_ENUM = frozenset({"simple", "developer"})
PRODUCT_PATH_ENUM = frozenset({"chatgpt", "claude", "cursor", "other"})
PATH_ENUM = frozenset({"chatgpt", "claude", "cursor", "other", "feedback"})
KIND_ENUM = frozenset(
    {
        "copy_result",
        "copy_share_text",
        "copy_team",
        "native",
        "copy_badge",
        "x",
        "linkedin",
        "facebook",
        "reddit",
        "svg_linkedin",
        "svg_x",
        "svg_facebook",
        "svg_reddit",
        "svg_square",
        "svg_badge",
        "png_linkedin",
        "png_x",
        "png_facebook",
        "png_square",
        "png_badge",
    }
)
TRAFFIC_CLASS_ENUM = frozenset({"production", "synthetic_qa"})
TRAFFIC_CLASS_SCHEMA = {
    "type": "string",
    "enum": TRAFFIC_CLASS_ENUM,
    "max_length": 16,
}


def _bucket_schema() -> dict[str, Any]:
    return {
        "type": "integer",
        "enum": set(BUCKETS),
        "min": min(BUCKETS),
        "max": max(BUCKETS),
    }


EVENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "cs_site_view": {
        "required": ("source",),
        "properties": {
            "source": {"type": "string", "enum": SOURCE_ENUM, "max_length": 24},
        },
    },
    "cs_rules_expand": {"required": (), "properties": {}},
    "cs_fix_plan": {"required": (), "properties": {}},
    "cs_fix_cancel": {"required": (), "properties": {}},
    "cs_export": {"required": (), "properties": {}},
    "cs_score": {
        "required": ("source", "profile", "ruleset", "overall_bucket", "controls_found"),
        "properties": {
            "source": {"type": "string", "enum": SOURCE_ENUM, "max_length": 24},
            "profile": {"type": "string", "enum": PROFILE_ENUM, "max_length": 24},
            "ruleset": {"type": "string", "pattern": RULESET_RE, "max_length": 40},
            "overall_bucket": _bucket_schema(),
            "controls_found": {"type": "integer", "min": 0, "max": CONTROL_MAX},
            "product_path": {"type": "string", "enum": PRODUCT_PATH_ENUM, "max_length": 24},
            "smell_count": {"type": "integer", "min": 0, "max": CONTROL_MAX},
            "delta_bucket": _bucket_schema(),
        },
    },
    "cs_vendor_open": {
        "required": ("kind",),
        "properties": {"kind": {"type": "string", "enum": {"summary"}, "max_length": 20}},
    },
    "cs_demo_started": {"required": (), "properties": {}},
    "cs_check_completed": {
        "required": ("source", "profile", "ruleset"),
        "properties": {
            "source": {"type": "string", "enum": SOURCE_ENUM, "max_length": 24},
            "profile": {"type": "string", "enum": PROFILE_ENUM, "max_length": 24},
            "ruleset": {"type": "string", "pattern": RULESET_RE, "max_length": 40},
        },
    },
    "cs_fix_review": {
        "required": ("dims_to_fix_count",),
        "properties": {"dims_to_fix_count": {"type": "integer", "min": 0, "max": CONTROL_MAX}},
    },
    "cs_mode_change": {
        "required": ("mode",),
        "properties": {"mode": {"type": "string", "enum": MODE_ENUM, "max_length": 12}},
    },
    "cs_share": {
        "required": ("kind",),
        "properties": {"kind": {"type": "string", "enum": KIND_ENUM, "max_length": 40}},
    },
    "cs_product_path": {
        "required": ("path",),
        "properties": {"path": {"type": "string", "enum": PATH_ENUM, "max_length": 24}},
    },
    "cs_fix_apply": {
        "required": ("controls_found",),
        "properties": {"controls_found": {"type": "integer", "min": 0, "max": CONTROL_MAX}},
    },
}

# Capture classification is optional for callers and bounded for every event.
for _event_schema in EVENT_SCHEMAS.values():
    _event_schema["properties"]["traffic_class"] = dict(TRAFFIC_CLASS_SCHEMA)

EVENT_REQUIRED_PROPERTIES = {event: spec.get("required", ()) for event, spec in EVENT_SCHEMAS.items()}
EVENT_OPTIONAL_PROPERTIES = {
    event: tuple(name for name in spec["properties"] if name not in spec.get("required", ()))
    for event, spec in EVENT_SCHEMAS.items()
}

# Must match analytics.js ALLOWED_EVENTS.
ALLOWED_EVENTS = frozenset(EVENT_SCHEMAS)

# Must match analytics.js ALLOWED_PROPERTIES.
ALLOWED_PROPERTIES = frozenset(
    {
        "source",
        "profile",
        "overall_bucket",
        "ruleset",
        "dims_to_fix_count",
        "delta_bucket",
        "kind",
        "mode",
        "path",
        "product_path",
        "controls_found",
        "smell_count",
        "traffic_class",
    }
)

# Keys that must never appear in payloads.
FORBIDDEN_PROP_KEYS = frozenset(
    {
        "prompt",
        "text",
        "body",
        "system_prompt",
        "content",
    }
)

CAPTURE_FORBIDDEN_PROP_KEYS = frozenset(
    {
        *FORBIDDEN_PROP_KEYS,
        "snippet",
        "input",
        "source_text",
    }
)

# Regexes used to keep Python↔JS schema parity checks stable.
_JS_SET_RE = re.compile(
    r"const\s+(ALLOWED_EVENTS|ALLOWED_PROPERTIES)\s*=\s*new\s+Set\(\[(.*?)\]\)",
    re.DOTALL,
)
_JS_STRING_RE = re.compile(r'"([^"\\]+)"')


def _raise(event: str, issue: str) -> None:
    raise ValueError(f"analytics event {event!r} invalid: {issue}")


def _validate_int(value: Any, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise ValueError("integer required")
    if not isinstance(value, int):
        raise ValueError("integer required")
    if minimum is not None and value < minimum:
        raise ValueError("integer below minimum")
    if maximum is not None and value > maximum:
        raise ValueError("integer above maximum")
    return value


def _validate_string(
    value: Any,
    *,
    enum: frozenset[str] | None = None,
    max_length: int = 80,
    pattern: re.Pattern[str] | None = None,
) -> str:
    if not isinstance(value, str):
        raise ValueError("string required")
    text = value.strip()
    if not text:
        raise ValueError("empty string")
    if len(text) > max_length:
        raise ValueError("string too long")
    if enum is not None and len(enum) and text not in enum:
        raise ValueError("unrecognized enum")
    if pattern is not None and not pattern.match(text):
        raise ValueError("pattern mismatch")
    return text


def _validate_event(event: str, props: dict[str, Any]) -> dict[str, Any]:
    schema = EVENT_SCHEMAS.get(event)
    if schema is None:
        _raise(event, "event not allowlisted")

    required = tuple(schema.get("required", ()))
    properties = schema.get("properties", {})

    for key in required:
        if key not in props:
            _raise(event, f"missing required property {key!r}")

    for key in props:
        if key not in properties:
            if event == "cs_score" and key in EVENT_OPTIONAL_PROPERTIES.get(event, ()):
                continue
            _raise(event, f"unexpected property {key!r}")

    out: dict[str, Any] = {}
    for key, spec in properties.items():
        if key not in props:
            continue
        value = props[key]
        if spec["type"] == "string":
            enum = spec.get("enum")
            out[key] = _validate_string(
                value,
                enum=frozenset(enum) if enum else None,
                max_length=spec.get("max_length", 80),
                pattern=spec.get("pattern"),
            )
        elif spec["type"] == "integer":
            value = _validate_int(value, minimum=spec.get("min"), maximum=spec.get("max"))
            enum = spec.get("enum")
            if enum is not None and value not in enum:
                _raise(event, f"{key} must be one of {sorted(enum)}")
            out[key] = value
        else:
            _raise(event, f"unsupported schema type {spec['type']!r}")
    return out


def _normalize_schema_spec(spec: dict[str, Any]) -> dict[str, Any]:
    out = dict(spec)
    if isinstance(out.get("pattern"), re.Pattern):
        out["pattern"] = out["pattern"].pattern
    enum = out.get("enum")
    if enum is not None:
        out["enum"] = sorted(enum)
    return out


def bucket_score(n: int | float) -> str:
    """Map an overall score to a privacy-safe bucket string."""
    score = int(n) if n is not None else 0
    if score <= 0:
        return "0"
    if score < 50:
        return "1-49"
    if score < 70:
        return "50-69"
    if score < 90:
        return "70-89"
    return "90-100"


def validate_props(props: dict[str, Any] | None) -> bool:
    """Validate legacy payload content.

    This keeps the 0.6.9 contract: one positional payload argument and
    forbid-only checks for free-text keys.
    """
    if not props:
        return True
    for key in props:
        if str(key).lower() in FORBIDDEN_PROP_KEYS:
            raise ValueError(f"metrics props must not include prompt text key: {key!r}")
    return True


def validate_event(event: str, props: dict[str, Any] | None = None) -> bool:
    """Validate the published 0.6.9 event contract.

    The public API intentionally remains allowlist-plus-content-safety only.
    Browser-bound callers use ``validate_capture_event`` for the strict schema.
    """
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"unknown metrics event: {event!r}")
    validate_props(props)
    return True


def validate_capture_event(event: str, props: dict[str, Any] | None = None) -> bool:
    """Validate a network-bound event against the strict capture schema."""
    if event not in ALLOWED_EVENTS:
        _raise(event, "event not allowlisted")
    if props is None:
        props = {}
    if not isinstance(props, dict):
        _raise(event, "properties must be an object")
    lowered = {str(key): value for key, value in props.items()}
    forbidden = {str(key).lower() for key in lowered}
    for key in CAPTURE_FORBIDDEN_PROP_KEYS:
        if key in forbidden:
            _raise(event, f"forbidden prompt-content key {key!r}")
    _validate_event(event, lowered)
    return True


def append_event(
    store: dict[str, Any] | None,
    event: str,
    props: dict[str, Any] | None = None,
    *,
    max_events: int = 200,
) -> dict[str, Any]:
    """Append a privacy-checked event; preserve the published 0.6.9 behavior."""
    props = dict(props or {})
    validate_event(event, props)
    out: dict[str, Any] = dict(store or {})
    events = list(out.get("events") or [])
    events.append(
        {
            "e": event,
            "t": int(time.time() * 1000),
            "p": props,
        }
    )
    if max_events > 0 and len(events) > max_events:
        events = events[-max_events:]
    out["events"] = events
    return out


def parse_analytics_allowlists(js_source: str) -> dict[str, frozenset[str]]:
    """Extract ALLOWED_EVENTS / ALLOWED_PROPERTIES from analytics.js source."""
    found: dict[str, frozenset[str]] = {}
    for match in _JS_SET_RE.finditer(js_source):
        name = match.group(1)
        body = match.group(2)
        found[name] = frozenset(_JS_STRING_RE.findall(body))
    return found


def schema_payload() -> dict[str, Any]:
    """Return the exact machine-readable contract published in 0.6.9."""
    return {
        "schema_version": SCHEMA_VERSION,
        "allowed_events": sorted(ALLOWED_EVENTS),
        "allowed_properties": sorted(ALLOWED_PROPERTIES),
        "forbidden_prop_keys": sorted(FORBIDDEN_PROP_KEYS),
        "score_buckets": list(SCORE_BUCKETS),
        "network": "web client only; Python core never sends metrics",
        "prompt_text": "never stored in event props",
    }


def capture_schema_payload() -> dict[str, Any]:
    """Machine-readable strict browser-capture contract."""
    return {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "allowed_events": sorted(ALLOWED_EVENTS),
        "allowed_properties": sorted(ALLOWED_PROPERTIES),
        "forbidden_prop_keys": sorted(CAPTURE_FORBIDDEN_PROP_KEYS),
        "score_buckets": list(BUCKETS),
        "prompt_text": "never stored in event props",
        "event_schemas": {
            event: {
                "required": list(EVENT_REQUIRED_PROPERTIES[event]),
                "properties": {
                    name: _normalize_schema_spec(dict(props))
                    for name, props in EVENT_SCHEMAS[event]["properties"].items()
                },
            }
            for event in sorted(EVENT_SCHEMAS)
        },
        "optional_properties": {
            event: list(properties) for event, properties in EVENT_OPTIONAL_PROPERTIES.items()
        },
    }
