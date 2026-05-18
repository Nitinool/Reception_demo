from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..events import Event, WindowSnapshot
from ..timeline import Timeline


class IdleCollector:
    def __init__(
        self,
        get_idle_seconds: Callable[[], float],
        idle_threshold_seconds: float = 60.0,
    ) -> None:
        self._get_idle_seconds = get_idle_seconds
        self.idle_threshold_seconds = idle_threshold_seconds
        self._is_idle = False
        self._idle_started_at: str | None = None

    def poll(self, timeline: Timeline, active_window: WindowSnapshot | None) -> list[Event]:
        idle_seconds = self._get_idle_seconds()

        if not self._is_idle and idle_seconds >= self.idle_threshold_seconds:
            event = timeline.create_event(
                "idle.started",
                "idle",
                active_window,
                {
                    "idle_threshold_seconds": self.idle_threshold_seconds,
                    "last_input_age_seconds": round(idle_seconds, 3),
                },
            )
            self._is_idle = True
            self._idle_started_at = event.timestamp
            return [event]

        if self._is_idle and idle_seconds < self.idle_threshold_seconds:
            ended_at = timeline.now()
            event = timeline.create_event(
                "idle.ended",
                "idle",
                active_window,
                {
                    "idle_started_at": self._idle_started_at,
                    "idle_ended_at": ended_at,
                    "duration_ms": self._duration_ms(self._idle_started_at, ended_at),
                },
                timestamp=ended_at,
            )
            self._is_idle = False
            self._idle_started_at = None
            return [event]

        return []

    @staticmethod
    def _duration_ms(started_at: str | None, ended_at: str) -> int:
        if started_at is None:
            return 0
        try:
            started = datetime.fromisoformat(started_at)
            ended = datetime.fromisoformat(ended_at)
        except ValueError:
            return 0
        return max(0, int((ended - started).total_seconds() * 1000))
