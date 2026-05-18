from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from behavior_logger.events import Event, WindowSnapshot
from behavior_logger.timeline import Timeline


class WindowCollector:
    def __init__(self, get_active_window: Callable[[], WindowSnapshot | None]) -> None:
        self._get_active_window = get_active_window
        self.current_window: WindowSnapshot | None = None
        self._focus_started_at: str | None = None

    def poll(self, timeline: Timeline) -> list[Event]:
        observed = self._get_active_window()
        if observed is None:
            # None is a transient unobservable sample, not a focus end.
            return []

        if self.current_window is None:
            event = self._focus_started(timeline, observed)
            self.current_window = observed
            self._focus_started_at = event.timestamp
            return [event]

        if self._is_different_window(observed):
            ended_at = timeline.now()
            ended = self._focus_ended(timeline, self.current_window, ended_at)
            started = self._focus_started(timeline, observed)
            self.current_window = observed
            self._focus_started_at = started.timestamp
            return [ended, started]

        if observed.title != self.current_window.title:
            event = timeline.create_event(
                type="window.title_changed",
                source="window",
                active_window=observed,
                data={
                    "window": {
                        "process_name": observed.process_name,
                        "process_id": observed.process_id,
                        "handle": observed.handle,
                    },
                    "old_title": self.current_window.title,
                    "new_title": observed.title,
                },
            )
            self.current_window = observed
            return [event]

        self.current_window = observed
        return []

    def _is_different_window(self, observed: WindowSnapshot) -> bool:
        if self.current_window is None:
            return False
        return (
            observed.handle != self.current_window.handle
            or observed.process_id != self.current_window.process_id
        )

    def _focus_started(self, timeline: Timeline, window: WindowSnapshot) -> Event:
        return timeline.create_event(
            type="window.focus_started",
            source="window",
            active_window=window,
            data={"window": window.to_dict()},
        )

    def _focus_ended(
        self,
        timeline: Timeline,
        window: WindowSnapshot,
        ended_at: str,
    ) -> Event:
        started_at = self._focus_started_at or ended_at
        return timeline.create_event(
            type="window.focus_ended",
            source="window",
            active_window=window,
            timestamp=ended_at,
            data={
                "window": window.to_dict(),
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_ms": _duration_ms(started_at, ended_at),
            },
        )


def _duration_ms(started_at: str, ended_at: str) -> int:
    try:
        started = datetime.fromisoformat(started_at)
        ended = datetime.fromisoformat(ended_at)
    except ValueError:
        return 0
    return max(0, int((ended - started).total_seconds() * 1000))
