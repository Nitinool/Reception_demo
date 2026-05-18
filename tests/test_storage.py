import json
from pathlib import Path
import tempfile
import unittest

from behavior_logger.events import Event
from behavior_logger.storage import EventStore


def sample_event(sequence=1, type="recording.started"):
    return Event(
        id=f"evt_{sequence}",
        timestamp=f"2026-05-17T17:40:1{sequence}.000+08:00",
        schema_version=1,
        type=type,
        source=type.split(".")[0],
        session_id="run_test",
        sequence=sequence,
        context={},
        data={"value": sequence},
    )


class EventStoreTests(unittest.TestCase):
    def test_insert_and_query_recent_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "behavior.db")
            store.initialize()
            store.insert(sample_event(1))
            store.insert(sample_event(2, "window.focus_started"))

            events = store.query_recent(limit=10)

            self.assertEqual([event["id"] for event in events], ["evt_2", "evt_1"])
            self.assertEqual(events[0]["data"], {"value": 2})

    def test_query_recent_filters_by_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "behavior.db")
            store.initialize()
            store.insert(sample_event(1))
            store.insert(sample_event(2, "window.focus_started"))

            events = store.query_recent(limit=10, type_filter="window.focus_started")

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["type"], "window.focus_started")

    def test_export_jsonl_writes_events_in_chronological_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "behavior.db")
            store.initialize()
            store.insert(sample_event(1))
            store.insert(sample_event(2))
            output = Path(tmp) / "events.jsonl"

            store.export_jsonl(output)

            lines = output.read_text(encoding="utf-8").splitlines()
            decoded = [json.loads(line) for line in lines]
            self.assertEqual([event["id"] for event in decoded], ["evt_1", "evt_2"])


if __name__ == "__main__":
    unittest.main()
