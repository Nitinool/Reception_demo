import unittest

from behavior_logger.events import WindowSnapshot
from behavior_logger.runner import LoggerRunner
from behavior_logger.timeline import Timeline


class FakeStore:
    def __init__(self):
        self.initialized = False
        self.events = []

    def initialize(self):
        self.initialized = True

    def insert(self, event):
        self.events.append(event)


class FakeWindowCollector:
    def __init__(self, events=None):
        self.current_window = WindowSnapshot(1, 10, "Code.exe", "main.py")
        self.events = events or []

    def poll(self, timeline):
        return self.events


class FakeIdleCollector:
    def __init__(self, events=None):
        self.idle_threshold_seconds = 60.0
        self.events = events or []
        self.observed_windows = []

    def poll(self, timeline, active_window):
        self.observed_windows.append(active_window)
        return self.events


class LoggerRunnerTests(unittest.TestCase):
    def test_poll_once_writes_window_events_then_idle_events(self):
        timeline = Timeline(
            "run_test",
            now=lambda: "t",
            id_factory=lambda: "evt",
        )
        window_event = timeline.create_event("window.focus_started", "window", None, {})
        idle_event = timeline.create_event("idle.started", "idle", None, {})
        store = FakeStore()
        window_collector = FakeWindowCollector([window_event])
        idle_collector = FakeIdleCollector([idle_event])
        runner = LoggerRunner(store, timeline, window_collector, idle_collector)

        events = runner.poll_once()

        self.assertEqual(events, [window_event, idle_event])
        self.assertEqual(store.events, [window_event, idle_event])
        self.assertEqual(idle_collector.observed_windows, [window_collector.current_window])

    def test_run_forever_writes_started_and_stopped_when_sleep_interrupts(self):
        timeline = Timeline(
            "run_test",
            now=lambda: "t",
            id_factory=lambda: "evt",
        )
        store = FakeStore()
        window_collector = FakeWindowCollector()
        idle_collector = FakeIdleCollector()

        def interrupt_after_poll(seconds):
            raise KeyboardInterrupt

        runner = LoggerRunner(
            store,
            timeline,
            window_collector,
            idle_collector,
            poll_interval_seconds=2.5,
            sleep=interrupt_after_poll,
        )

        runner.run_forever()

        self.assertTrue(store.initialized)
        self.assertEqual([event.type for event in store.events], [
            "recording.started",
            "recording.stopped",
        ])
        self.assertEqual(
            store.events[0].data["config"],
            {"poll_interval_seconds": 2.5, "idle_threshold_seconds": 60.0},
        )
        self.assertEqual(store.events[1].data, {"reason": "user_interrupt"})
        self.assertEqual(
            store.events[1].context["active_window"]["process_name"],
            "Code.exe",
        )

    def test_run_forever_records_exception_reason_and_reraises(self):
        timeline = Timeline(
            "run_test",
            now=lambda: "t",
            id_factory=lambda: "evt",
        )
        store = FakeStore()
        window_collector = FakeWindowCollector()
        idle_collector = FakeIdleCollector()

        def raise_runtime_error(seconds):
            raise RuntimeError("boom")

        runner = LoggerRunner(
            store,
            timeline,
            window_collector,
            idle_collector,
            sleep=raise_runtime_error,
        )

        with self.assertRaises(RuntimeError):
            runner.run_forever()

        self.assertEqual([event.type for event in store.events], [
            "recording.started",
            "recording.stopped",
        ])
        self.assertEqual(store.events[1].data, {"reason": "exception:RuntimeError"})


if __name__ == "__main__":
    unittest.main()
