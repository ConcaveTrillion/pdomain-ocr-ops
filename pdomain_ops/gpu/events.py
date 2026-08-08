"""Parse the worker `@@PDEVENT@@` stdout line protocol into JobEvent payloads.

A worker subprocess supervised by `LocalLongJobRunner` may emit structured
progress on stdout, one line per event:

    @@PDEVENT@@ {"kind": "progress", "payload": {"pct": 0.5}}

`kind` must be one of the `JobEvent` literals (progress / log / state /
metric). Lines without the prefix are ordinary log output, not events.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeGuard

EVENT_PREFIX = "@@PDEVENT@@"

_VALID_KINDS = frozenset({"progress", "log", "state", "metric"})


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """Narrow a decoded JSON value to an object; JSON keys are always strings."""
    return isinstance(value, dict)


def is_event_line(line: str) -> bool:
    """True when `line` carries a structured `@@PDEVENT@@` payload."""
    return line.lstrip().startswith(EVENT_PREFIX)


def parse_event_line(line: str) -> tuple[str, dict[str, object]]:
    """Parse one `@@PDEVENT@@` line into a `(kind, payload)` pair.

    Raises ValueError when the line is not a well-formed event line so the
    supervisor can log and skip without crashing.
    """
    stripped = line.lstrip()
    if not stripped.startswith(EVENT_PREFIX):
        raise ValueError(f"not a @@PDEVENT@@ line: {line!r}")
    body = stripped[len(EVENT_PREFIX) :].strip()
    try:
        raw: object = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed @@PDEVENT@@ payload: {body!r}") from exc

    if not _is_json_object(raw):
        raise ValueError(f"@@PDEVENT@@ payload is not an object: {body!r}")

    kind = raw.get("kind")
    if kind not in _VALID_KINDS:
        raise ValueError(f"invalid @@PDEVENT@@ kind: {kind!r}")

    payload = raw.get("payload", {})
    if not _is_json_object(payload):
        raise ValueError(f"@@PDEVENT@@ payload field is not an object: {payload!r}")

    return str(kind), payload
