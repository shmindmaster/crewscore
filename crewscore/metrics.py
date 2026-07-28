"""Privacy-safe local metrics schema (no network, never store prompt text).

Schema authority for event names/buckets used by web localStorage
(`crewscore_metrics_v1`) and any future CLI counters.
"""

from __future__ import annotations

import time
from typing import Any

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
    validate_props(props)

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
