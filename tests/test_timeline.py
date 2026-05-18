import unittest

from behavior_logger.events import WindowSnapshot
from behavior_logger.timeline import Timeline


class TimelineTests(unittest.TestCase):
    def test_create_event_assigns_session_sequence_timestamp_and_context(self):
        timeline = Timeline(
            session_id="run_test",
            now=lambda: "2026-05-17T17:40:12.123+08:00",
            id_factory=lambda: "evt_test",
        )
        active_window = WindowSnapshot(1, 2, "Code.exe", "main.py")

        event = timeline.create_event(
            type="window.focus_started",
            source="window",
            active_window=active_window,
            data={"window": active_window.to_dict()},
        )

        self.assertEqual(event.id, "evt_test")
        self.assertEqual(event.timestamp, "2026-05-17T17:40:12.123+08:00")
        self.assertEqual(event.session_id, "run_test")
        self.assertEqual(event.sequence, 1)
        self.assertEqual(event.context["active_window"]["process_name"], "Code.exe")

    def test_sequence_increments_with_each_event(self):
        timeline = Timeline(
            session_id="run_test",
            now=lambda: "2026-05-17T17:40:12.123+08:00",
            id_factory=lambda: "evt_test",
        )

        first = timeline.create_event("recording.started", "recording", None, {})
        second = timeline.create_event("recording.stopped", "recording", None, {})

        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)

    def test_create_event_can_use_explicit_timestamp(self):
        timeline = Timeline(
            session_id="run_test",
            now=lambda: "clock_time",
            id_factory=lambda: "evt_test",
        )

        event = timeline.create_event(
            "window.focus_ended",
            "window",
            None,
            {},
            timestamp="explicit_time",
        )

        self.assertEqual(event.timestamp, "explicit_time")


if __name__ == "__main__":
    unittest.main()
