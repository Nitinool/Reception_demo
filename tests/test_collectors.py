import unittest

from behavior_logger.collectors.window import WindowCollector
from behavior_logger.collectors.idle import IdleCollector
from behavior_logger.events import WindowSnapshot
from behavior_logger.timeline import Timeline


class WindowCollectorTests(unittest.TestCase):
    def test_first_seen_window_emits_focus_started(self):
        timeline = Timeline("run_test", now=lambda: "t1", id_factory=lambda: "evt")
        window = WindowSnapshot(1, 10, "Code.exe", "main.py")
        collector = WindowCollector(lambda: window)

        events = collector.poll(timeline)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "window.focus_started")
        self.assertEqual(events[0].data["window"]["title"], "main.py")

    def test_focus_change_emits_end_then_start(self):
        times = iter(["t1", "t2", "t3"])
        timeline = Timeline("run_test", now=lambda: next(times), id_factory=lambda: "evt")
        first = WindowSnapshot(1, 10, "Code.exe", "main.py")
        second = WindowSnapshot(2, 20, "Chrome.exe", "ChatGPT")
        current = [first]
        collector = WindowCollector(lambda: current[0])
        collector.poll(timeline)

        current[0] = second
        events = collector.poll(timeline)

        self.assertEqual([event.type for event in events], ["window.focus_ended", "window.focus_started"])
        self.assertEqual(events[0].data["window"]["process_name"], "Code.exe")
        self.assertEqual(events[0].data["started_at"], "t1")
        self.assertEqual(events[0].data["ended_at"], "t2")
        self.assertEqual(events[1].data["window"]["process_name"], "Chrome.exe")

    def test_none_sample_is_ignored_and_preserves_current_window(self):
        timeline = Timeline("run_test", now=lambda: "t1", id_factory=lambda: "evt")
        window = WindowSnapshot(1, 10, "Code.exe", "main.py")
        current = [window]
        collector = WindowCollector(lambda: current[0])
        collector.poll(timeline)

        current[0] = None
        none_events = collector.poll(timeline)

        self.assertEqual(none_events, [])
        self.assertEqual(collector.current_window, window)

        current[0] = window
        resumed_events = collector.poll(timeline)

        self.assertEqual(resumed_events, [])
        self.assertEqual(collector.current_window, window)

    def test_title_change_emits_title_changed(self):
        times = iter(["t1", "t2"])
        timeline = Timeline("run_test", now=lambda: next(times), id_factory=lambda: "evt")
        current = [WindowSnapshot(1, 10, "Code.exe", "main.py")]
        collector = WindowCollector(lambda: current[0])
        collector.poll(timeline)

        current[0] = WindowSnapshot(1, 10, "Code.exe", "README.md")
        events = collector.poll(timeline)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "window.title_changed")
        self.assertEqual(events[0].data["old_title"], "main.py")
        self.assertEqual(events[0].data["new_title"], "README.md")


class IdleCollectorTests(unittest.TestCase):
    def test_idle_started_and_ended_are_transitions_only(self):
        timeline = Timeline("run_test", now=lambda: "t", id_factory=lambda: "evt")
        idle_age = [0.0]
        collector = IdleCollector(lambda: idle_age[0], idle_threshold_seconds=60)

        self.assertEqual(collector.poll(timeline, active_window=None), [])

        idle_age[0] = 61.0
        started = collector.poll(timeline, active_window=None)
        self.assertEqual(started[0].type, "idle.started")

        still_idle = collector.poll(timeline, active_window=None)
        self.assertEqual(still_idle, [])

        idle_age[0] = 0.5
        ended = collector.poll(timeline, active_window=None)
        self.assertEqual(ended[0].type, "idle.ended")

    def test_idle_events_include_context_and_duration_when_timestamps_are_iso(self):
        times = iter([
            "2026-05-17T17:55:12.000+08:00",
            "2026-05-17T17:56:20.000+08:00",
        ])
        timeline = Timeline("run_test", now=lambda: next(times), id_factory=lambda: "evt")
        idle_age = [61.0]
        active_window = WindowSnapshot(1, 10, "Code.exe", "main.py")
        collector = IdleCollector(lambda: idle_age[0], idle_threshold_seconds=60)

        started = collector.poll(timeline, active_window=active_window)
        idle_age[0] = 0.5
        ended = collector.poll(timeline, active_window=active_window)

        self.assertEqual(started[0].context["active_window"]["process_name"], "Code.exe")
        self.assertEqual(ended[0].data["duration_ms"], 68000)


if __name__ == "__main__":
    unittest.main()
