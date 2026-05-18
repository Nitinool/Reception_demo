import contextlib
import importlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

from behavior_logger.cli import build_parser, export_command, main, tail_command
from behavior_logger.events import Event
from behavior_logger.storage import EventStore


def sample_event(sequence=1, type="recording.started"):
    return Event(
        id=f"evt_{sequence}",
        timestamp=f"2026-05-17T17:40:1{sequence}.000+08:00",
        schema_version=1,
        type=type,
        source=type.split(".")[0],
        session_id="cli_test",
        sequence=sequence,
        context={},
        data={"value": sequence},
    )


class CliTests(unittest.TestCase):
    def test_importing_cli_does_not_load_windows_api(self):
        sys.modules.pop("behavior_logger.cli", None)
        sys.modules.pop("behavior_logger.windows_api", None)

        cli = importlib.import_module("behavior_logger.cli")

        self.assertNotIn("behavior_logger.windows_api", sys.modules)
        globals()["build_parser"] = cli.build_parser
        globals()["export_command"] = cli.export_command
        globals()["main"] = cli.main
        globals()["tail_command"] = cli.tail_command

    def test_run_defaults(self):
        args = build_parser().parse_args(["run"])

        self.assertEqual(args.command, "run")
        self.assertEqual(args.db, "data/behavior.db")
        self.assertEqual(args.poll_interval, 1.0)
        self.assertEqual(args.idle_threshold, 60.0)

    def test_tail_defaults(self):
        args = build_parser().parse_args(["tail"])

        self.assertEqual(args.command, "tail")
        self.assertEqual(args.limit, 50)
        self.assertIsNone(args.type)

    def test_export_requires_output_path(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["export"])

    def test_export_missing_database_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "missing.db"
            out_path = Path(tmp) / "events.jsonl"
            args = build_parser().parse_args(["export", "--db", str(db_path), "--out", str(out_path)])

            with self.assertRaises(FileNotFoundError):
                export_command(args)

            self.assertFalse(db_path.exists())

    def test_tail_prints_recent_events_oldest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "behavior.db"
            store = EventStore(db_path)
            store.initialize()
            store.insert(sample_event(1))
            store.insert(sample_event(2))
            args = build_parser().parse_args(["tail", "--db", str(db_path), "--limit", "2"])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                result = tail_command(args)

            self.assertEqual(result, 0)
            lines = stdout.getvalue().splitlines()
            self.assertEqual(lines, ["17:40:11 recording.started", "17:40:12 recording.started"])

    def test_export_writes_jsonl_and_prints_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "behavior.db"
            out_path = Path(tmp) / "events.jsonl"
            store = EventStore(db_path)
            store.initialize()
            store.insert(sample_event(1))
            args = build_parser().parse_args(["export", "--db", str(db_path), "--out", str(out_path)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                result = export_command(args)

            self.assertEqual(result, 0)
            self.assertEqual(len(out_path.read_text(encoding="utf-8").splitlines()), 1)
            self.assertEqual(stdout.getvalue().strip(), f"Exported 1 events to {out_path}")

    def test_main_dispatches_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "behavior.db"
            store = EventStore(db_path)
            store.initialize()
            store.insert(sample_event(1))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                result = main(["tail", "--db", str(db_path), "--limit", "1"])

            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue().strip(), "17:40:11 recording.started")


if __name__ == "__main__":
    unittest.main()
