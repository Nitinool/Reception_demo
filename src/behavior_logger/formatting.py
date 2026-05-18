from __future__ import annotations

from datetime import datetime
from typing import Any


def format_event_line(event: dict[str, Any]) -> str:
    time_part = _time_part(event["timestamp"])
    event_type = event["type"]
    data = event.get("data", {})

    if event_type == "window.focus_started":
        window = data.get("window", {})
        return f"{time_part} {event_type} {window.get('process_name', '')} | {window.get('title', '')}"

    if event_type == "window.focus_ended":
        window = data.get("window", {})
        return f"{time_part} {event_type} {window.get('process_name', '')} | {data.get('duration_ms', 0)}ms"

    if event_type == "window.title_changed":
        return f"{time_part} {event_type} {data.get('old_title', '')} -> {data.get('new_title', '')}"

    if event_type == "idle.ended":
        return f"{time_part} {event_type} | {data.get('duration_ms', 0)}ms"

    return f"{time_part} {event_type}"


def _time_part(timestamp: str) -> str:
    try:
        return datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
    except ValueError:
        return timestamp[:8]
