from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import uuid

from .events import Event, SCHEMA_VERSION, WindowSnapshot


def default_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_event_id() -> str:
    return f"evt_{uuid.uuid4().hex}"


def default_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"run_{stamp}_{uuid.uuid4().hex[:8]}"


class Timeline:
    def __init__(
        self,
        session_id: str | None = None,
        now: Callable[[], str] = default_now,
        id_factory: Callable[[], str] = default_event_id,
    ) -> None:
        self.session_id = session_id or default_session_id()
        self._now = now
        self._id_factory = id_factory
        self._sequence = 0

    def create_event(
        self,
        type: str,
        source: str,
        active_window: WindowSnapshot | None,
        data: dict,
        timestamp: str | None = None,
    ) -> Event:
        self._sequence += 1
        context = {}
        if active_window is not None:
            context["active_window"] = active_window.to_dict()

        return Event(
            id=self._id_factory(),
            timestamp=timestamp or self.now(),
            schema_version=SCHEMA_VERSION,
            type=type,
            source=source,
            session_id=self.session_id,
            sequence=self._sequence,
            context=context,
            data=data,
        )

    def now(self) -> str:
        return self._now()
