from __future__ import annotations

import argparse
from pathlib import Path

from .collectors.idle import IdleCollector
from .collectors.window import WindowCollector
from .formatting import format_event_line
from .runner import LoggerRunner
from .storage import EventStore
from .timeline import Timeline


DEFAULT_DB = "data/behavior.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="behavior_logger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Start collecting desktop behavior events")
    run_parser.add_argument("--db", default=DEFAULT_DB)
    run_parser.add_argument("--poll-interval", type=float, default=1.0)
    run_parser.add_argument("--idle-threshold", type=float, default=60.0)

    tail_parser = subparsers.add_parser("tail", help="Show recent events")
    tail_parser.add_argument("--db", default=DEFAULT_DB)
    tail_parser.add_argument("--limit", type=int, default=50)
    tail_parser.add_argument("--type", default=None)

    export_parser = subparsers.add_parser("export", help="Export events as JSONL")
    export_parser.add_argument("--db", default=DEFAULT_DB)
    export_parser.add_argument("--out", required=True)
    export_parser.add_argument("--type", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "run":
        return run_command(args)
    if args.command == "tail":
        return tail_command(args)
    if args.command == "export":
        return export_command(args)
    raise ValueError(f"Unknown command: {args.command}")


def run_command(args: argparse.Namespace) -> int:
    from .windows_api import get_active_window, get_idle_seconds

    store = EventStore(Path(args.db))
    timeline = Timeline()
    runner = LoggerRunner(
        store=store,
        timeline=timeline,
        window_collector=WindowCollector(get_active_window),
        idle_collector=IdleCollector(get_idle_seconds, args.idle_threshold),
        poll_interval_seconds=args.poll_interval,
    )
    runner.run_forever()
    return 0


def tail_command(args: argparse.Namespace) -> int:
    store = EventStore(Path(args.db))
    store.initialize()
    events = store.query_recent(limit=args.limit, type_filter=args.type)
    for event in reversed(events):
        print(format_event_line(event))
    return 0


def export_command(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    store = EventStore(db_path)
    store.initialize()
    count = store.export_jsonl(args.out, type_filter=args.type)
    print(f"Exported {count} events to {args.out}")
    return 0
