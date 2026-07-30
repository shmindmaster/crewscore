"""Privacy-safe metrics schema (no network from Python, never store prompt text).

Authoritative lists for event names and property keys used by the static site
(`analytics.js`) and any future CLI counters. Keep this module and
`analytics.js` in lockstep — `tests/test_metrics.py` enforces parity.
"""

from __future__ import annotations

import re
import time
from typing import Any

# Bump when allowlists change; analytics.js must carry the same string.
SCHEMA_VERSION = "2026-07-28"

# Keys that must never appear in metrics payloads (case-insensitive).
FORBIDDEN_PROP_KEYS = frozenset(
    {
        "prompt",
        "text",
        "body",
        "system_prompt",
        "content",
    }
)

# Must match analytics.js ALLOWED_EVENTS.
ALLOWED_EVENTS = frozenset(
    {
        "cs_site_view",
        "cs_rules_expand",
        "cs_fix_plan",
        "cs_fix_cancel",
        "cs_fix_apply",
        "cs_export",
        "cs_score",
        "cs_vendor_open",
        "cs_demo_started",
        "cs_check_completed",
        "cs_fix_review",
        "cs_mode_change",
        "cs_share",
    }
)

# Must match analytics.js ALLOWED_PROPERTIES.
ALLOWED_PROPERTIES = frozenset(
    {
        "source",
        "profile",
        "overall_bucket",
        "smell_count",
        "ruleset",
        "dims_to_fix_count",
        "delta_bucket",
        "kind",
        "controls_found",
        "mode",
    }
)

SCORE_BUCKETS = ("0", "1-49", "50-69", "70-89", "90-100")


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
    """Reject payloads that could carry prompt or free-text body content.

    Raises ValueError when a forbidden key is present (case-insensitive).
    Returns True when props are safe.
    """
    if not props:
        return True
    for key in props:
        if str(key).lower() in FORBIDDEN_PROP_KEYS:
            raise ValueError(
                f"metrics props must not include prompt text key: {key!r}"
            )
    return True


def validate_event(event: str, props: dict[str, Any] | None = None) -> bool:
    """Validate event name against the public allowlist and props for safety.

    Raises ValueError on unknown event or forbidden prop keys.
    Does not require props to be a subset of ALLOWED_PROPERTIES so local
    stores can carry extra non-content keys (e.g. test indices); the web
    client strips unknown keys before network send.
    """
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"unknown metrics event: {event!r}")
    validate_props(props)
    return True


def append_event(
    store: dict[str, Any] | None,
    event: str,
    props: dict[str, Any] | None = None,
    *,
    max_events: int = 200,
) -> dict[str, Any]:
    """Append a privacy-checked event; cap store size to max_events (newest kept).

    Store shape matches web localStorage:
      {"events": [{"e": name, "t": epoch_ms, "p": props}, ...]}
    """
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


_JS_SET_RE = re.compile(
    r"const\s+(ALLOWED_EVENTS|ALLOWED_PROPERTIES)\s*=\s*new\s+Set\(\[(.*?)\]\)",
    re.DOTALL,
)
_JS_STRING_RE = re.compile(r'"([^"\\]+)"')


def parse_analytics_allowlists(js_source: str) -> dict[str, frozenset[str]]:
    """Extract ALLOWED_EVENTS / ALLOWED_PROPERTIES from analytics.js source."""
    found: dict[str, frozenset[str]] = {}
    for match in _JS_SET_RE.finditer(js_source):
        name = match.group(1)
        body = match.group(2)
        found[name] = frozenset(_JS_STRING_RE.findall(body))
    return found


def schema_payload() -> dict[str, Any]:
    """Machine-readable metrics contract for docs and parity tests."""
    return {
        "schema_version": SCHEMA_VERSION,
        "allowed_events": sorted(ALLOWED_EVENTS),
        "allowed_properties": sorted(ALLOWED_PROPERTIES),
        "forbidden_prop_keys": sorted(FORBIDDEN_PROP_KEYS),
        "score_buckets": list(SCORE_BUCKETS),
        "network": "web client only; Python core never sends metrics",
        "prompt_text": "never stored in event props",
    }
