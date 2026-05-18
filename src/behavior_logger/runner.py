from __future__ import annotations

from collections.abc import Callable
import time

from .collectors.idle import IdleCollector
from .collectors.window import WindowCollector
from .events import Event
from .storage import EventStore
from .timeline import Timeline


class LoggerRunner:
    def __init__(
        self,
        store: EventStore,
        timeline: Timeline,
        window_collector: WindowCollector,
        idle_collector: IdleCollector,
        poll_interval_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.store = store
        self.timeline = timeline
        self.window_collector = window_collector
        self.idle_collector = idle_collector
        self.poll_interval_seconds = poll_interval_seconds
        self._sleep = sleep

    def run_forever(self) -> None:
        self.store.initialize()
        self._write(
            self.timeline.create_event(
                "recording.started",
                "recording",
                None,
                {
                    "config": {
                        "poll_interval_seconds": self.poll_interval_seconds,
                        "idle_threshold_seconds": self.idle_collector.idle_threshold_seconds,
                    }
                },
            )
        )

        stop_reason = "user_interrupt"
        try:
            while True:
                self.poll_once()
                self._sleep(self.poll_interval_seconds)
        except KeyboardInterrupt:
            stop_reason = "user_interrupt"
        except Exception as error:
            stop_reason = f"exception:{type(error).__name__}"
            raise
        finally:
            self._write(
                self.timeline.create_event(
                    "recording.stopped",
                    "recording",
                    self.window_collector.current_window,
                    {"reason": stop_reason},
                )
            )

    def poll_once(self) -> list[Event]:
        events: list[Event] = []
        events.extend(self.window_collector.poll(self.timeline))
        events.extend(self.idle_collector.poll(self.timeline, self.window_collector.current_window))
        for event in events:
            self._write(event)
        return events

    def _write(self, event: Event) -> None:
        self.store.insert(event)
