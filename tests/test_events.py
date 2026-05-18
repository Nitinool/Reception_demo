import unittest

from behavior_logger.events import Event, WindowSnapshot


class EventTests(unittest.TestCase):
    def test_event_to_record_serializes_context_and_data_as_json(self):
        event = Event(
            id="evt_1",
            timestamp="2026-05-17T17:40:12.123+08:00",
            schema_version=1,
            type="window.focus_started",
            source="window",
            session_id="run_1",
            sequence=1,
            context={"active_window": {"process_name": "Code.exe"}},
            data={"window": {"process_name": "Code.exe"}},
        )

        record = event.to_record()

        self.assertEqual(record["id"], "evt_1")
        self.assertEqual(record["type"], "window.focus_started")
        self.assertEqual(record["context_json"], '{"active_window":{"process_name":"Code.exe"}}')
        self.assertEqual(record["data_json"], '{"window":{"process_name":"Code.exe"}}')

    def test_window_snapshot_to_dict_uses_spec_field_names(self):
        window = WindowSnapshot(
            handle=123,
            process_id=456,
            process_name="Code.exe",
            title="main.py",
        )

        self.assertEqual(
            window.to_dict(),
            {
                "process_name": "Code.exe",
                "process_id": 456,
                "title": "main.py",
                "handle": 123,
            },
        )


if __name__ == "__main__":
    unittest.main()
