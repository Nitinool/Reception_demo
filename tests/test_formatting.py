import unittest

from behavior_logger.formatting import format_event_line


class FormattingTests(unittest.TestCase):
    def test_formats_window_focus_started(self):
        event = {
            "timestamp": "2026-05-17T17:52:03.000+08:00",
            "type": "window.focus_started",
            "data": {"window": {"process_name": "Code.exe", "title": "main.py"}},
        }

        self.assertEqual(
            format_event_line(event),
            "17:52:03 window.focus_started Code.exe | main.py",
        )

    def test_formats_duration_event(self):
        event = {
            "timestamp": "2026-05-17T17:54:10.000+08:00",
            "type": "window.focus_ended",
            "data": {"window": {"process_name": "Code.exe"}, "duration_ms": 127000},
        }

        self.assertEqual(
            format_event_line(event),
            "17:54:10 window.focus_ended Code.exe | 127000ms",
        )

    def test_formats_idle_ended(self):
        event = {
            "timestamp": "2026-05-17T17:55:20.000+08:00",
            "type": "idle.ended",
            "data": {"duration_ms": 30000},
        }

        self.assertEqual(
            format_event_line(event),
            "17:55:20 idle.ended | 30000ms",
        )

    def test_formats_title_changed(self):
        event = {
            "timestamp": "2026-05-17T17:56:01.000+08:00",
            "type": "window.title_changed",
            "data": {"old_title": "main.py", "new_title": "formatting.py"},
        }

        self.assertEqual(
            format_event_line(event),
            "17:56:01 window.title_changed main.py -> formatting.py",
        )


if __name__ == "__main__":
    unittest.main()
