# Windows Behavior Logger Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 Python CLI behavior logger for Windows foreground-window, title-change, and idle-transition events.

**Architecture:** The implementation uses small focused modules: event model, SQLite storage, timeline sequencing, Windows API adapter, collectors, runner, formatter, and CLI. Pure logic is tested with `unittest`; Windows API calls are isolated behind an adapter so collector behavior can be tested with fakes.

**Tech Stack:** Python 3, standard library only (`argparse`, `ctypes`, `dataclasses`, `json`, `sqlite3`, `unittest`).

---

## File Structure

- Create: `pyproject.toml`
  - Minimal project metadata and package discovery.
- Create: `src/behavior_logger/__init__.py`
  - Package version.
- Create: `src/behavior_logger/__main__.py`
  - Enables `python -m behavior_logger`.
- Create: `src/behavior_logger/events.py`
  - Event and window snapshot dataclasses.
- Create: `src/behavior_logger/timeline.py`
  - Session ID, sequence numbers, timestamp generation, event construction.
- Create: `src/behavior_logger/storage.py`
  - SQLite schema, insert, query, JSONL export.
- Create: `src/behavior_logger/windows_api.py`
  - Windows foreground-window and idle-time adapter via `ctypes`.
- Create: `src/behavior_logger/collectors/window.py`
  - Window focus and title change detection.
- Create: `src/behavior_logger/collectors/idle.py`
  - Idle start/end transition detection.
- Create: `src/behavior_logger/collectors/__init__.py`
  - Collector package marker.
- Create: `src/behavior_logger/runner.py`
  - Main polling loop and graceful stop event emission.
- Create: `src/behavior_logger/formatting.py`
  - Compact event formatting for `tail`.
- Create: `src/behavior_logger/cli.py`
  - `run`, `tail`, and `export` commands.
- Create: `tests/test_events.py`
  - Event serialization tests.
- Create: `tests/test_timeline.py`
  - Timeline sequencing and context tests.
- Create: `tests/test_storage.py`
  - SQLite schema, insert, query, export tests.
- Create: `tests/test_collectors.py`
  - Window and idle collector transition tests with fakes.
- Create: `tests/test_formatting.py`
  - Compact output formatting tests.
- Create: `tests/test_cli.py`
  - CLI argument parsing and command dispatch tests.

This folder is currently treated as a normal project folder, not a Git workflow. Use test checkpoints instead of commit checkpoints unless the user initializes Git later.

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/behavior_logger/__init__.py`
- Create: `src/behavior_logger/__main__.py`
- Create: `src/behavior_logger/collectors/__init__.py`

- [ ] **Step 1: Create package skeleton**

Write these files:

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "behavior-logger"
version = "0.1.0"
description = "Local Windows desktop behavior logger"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["src"]
```

```python
# src/behavior_logger/__init__.py
__version__ = "0.1.0"
```

```python
# src/behavior_logger/__main__.py
from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/behavior_logger/collectors/__init__.py
"""Collectors for observable desktop state."""
```

- [ ] **Step 2: Install the package in editable mode**

Run:

```powershell
python -m pip install -e .
```

Expected: Succeeds without downloading project dependencies because Phase 1 uses only the Python standard library.

- [ ] **Step 3: Run the empty test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: The command may report that `tests` does not exist yet. That is acceptable before Task 2.

## Task 2: Event Model

**Files:**
- Create: `src/behavior_logger/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write failing event serialization tests**

```python
# tests/test_events.py
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_events -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `Event`.

- [ ] **Step 3: Implement event model**

```python
# src/behavior_logger/events.py
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WindowSnapshot:
    handle: int
    process_id: int
    process_name: str
    title: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_name": self.process_name,
            "process_id": self.process_id,
            "title": self.title,
            "handle": self.handle,
        }


@dataclass(frozen=True)
class Event:
    id: str
    timestamp: str
    schema_version: int
    type: str
    source: str
    session_id: str
    sequence: int
    context: dict[str, Any]
    data: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "type": self.type,
            "source": self.source,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "context_json": json.dumps(self.context, ensure_ascii=False, separators=(",", ":")),
            "data_json": json.dumps(self.data, ensure_ascii=False, separators=(",", ":")),
        }

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "type": self.type,
            "source": self.source,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "context": self.context,
            "data": self.data,
        }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
python -m unittest tests.test_events -v
```

Expected: PASS.

## Task 3: Timeline Event Factory

**Files:**
- Create: `src/behavior_logger/timeline.py`
- Test: `tests/test_timeline.py`

- [ ] **Step 1: Write failing timeline tests**

```python
# tests/test_timeline.py
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_timeline -v
```

Expected: FAIL with missing `Timeline`.

- [ ] **Step 3: Implement timeline**

```python
# src/behavior_logger/timeline.py
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import uuid

from .events import Event, SCHEMA_VERSION, WindowSnapshot


def default_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_event_id() -> str:
    return f"evt_{uuid.uuid4().hex}"


def default_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"run_{stamp}_{uuid.uuid4().hex[:8]}"


class Timeline:
    def __init__(
        self,
        session_id: str | None = None,
        now: Callable[[], str] = default_now,
        id_factory: Callable[[], str] = default_event_id,
    ) -> None:
        self.session_id = session_id or default_session_id()
        self._now = now
        self._id_factory = id_factory
        self._sequence = 0

    def create_event(
        self,
        type: str,
        source: str,
        active_window: WindowSnapshot | None,
        data: dict,
        timestamp: str | None = None,
    ) -> Event:
        self._sequence += 1
        context = {}
        if active_window is not None:
            context["active_window"] = active_window.to_dict()

        return Event(
            id=self._id_factory(),
            timestamp=timestamp or self.now(),
            schema_version=SCHEMA_VERSION,
            type=type,
            source=source,
            session_id=self.session_id,
            sequence=self._sequence,
            context=context,
            data=data,
        )

    def now(self) -> str:
        return self._now()
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
python -m unittest tests.test_timeline -v
```

Expected: PASS.

## Task 4: SQLite Storage

**Files:**
- Create: `src/behavior_logger/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

```python
# tests/test_storage.py
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_storage -v
```

Expected: FAIL with missing `EventStore`.

- [ ] **Step 3: Implement SQLite storage**

```python
# src/behavior_logger/storage.py
from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any

from .events import Event


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  type TEXT NOT NULL,
  source TEXT NOT NULL,
  session_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  context_json TEXT NOT NULL,
  data_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_session_sequence ON events(session_id, sequence);
"""


class EventStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(SCHEMA)

    def insert(self, event: Event) -> None:
        record = event.to_record()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO events (
                    id, timestamp, schema_version, type, source,
                    session_id, sequence, context_json, data_json
                )
                VALUES (
                    :id, :timestamp, :schema_version, :type, :source,
                    :session_id, :sequence, :context_json, :data_json
                )
                """,
                record,
            )

    def query_recent(self, limit: int = 50, type_filter: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, timestamp, schema_version, type, source,
                   session_id, sequence, context_json, data_json
            FROM events
        """
        params: list[Any] = []
        if type_filter:
            sql += " WHERE type = ?"
            params.append(type_filter)
        sql += " ORDER BY timestamp DESC, sequence DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_event_dict(row) for row in rows]

    def export_jsonl(self, output_path: str | Path, type_filter: str | None = None) -> int:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        sql = """
            SELECT id, timestamp, schema_version, type, source,
                   session_id, sequence, context_json, data_json
            FROM events
        """
        params: list[Any] = []
        if type_filter:
            sql += " WHERE type = ?"
            params.append(type_filter)
        sql += " ORDER BY timestamp ASC, sequence ASC"

        count = 0
        with sqlite3.connect(self.db_path) as connection, output.open("w", encoding="utf-8") as file:
            for row in connection.execute(sql, params):
                event = self._row_to_event_dict(row)
                file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
        return count

    @staticmethod
    def _row_to_event_dict(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "id": row[0],
            "timestamp": row[1],
            "schema_version": row[2],
            "type": row[3],
            "source": row[4],
            "session_id": row[5],
            "sequence": row[6],
            "context": json.loads(row[7]),
            "data": json.loads(row[8]),
        }
```

- [ ] **Step 4: Run storage tests**

Run:

```powershell
python -m unittest tests.test_storage -v
```

Expected: PASS.

## Task 5: Window Collector

**Files:**
- Create: `src/behavior_logger/collectors/window.py`
- Test: `tests/test_collectors.py`

- [ ] **Step 1: Write failing window collector tests**

```python
# tests/test_collectors.py
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_collectors -v
```

Expected: FAIL because collector modules are missing.

- [ ] **Step 3: Implement window collector**

```python
# src/behavior_logger/collectors/window.py
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..events import Event, WindowSnapshot
from ..timeline import Timeline


class WindowCollector:
    def __init__(self, get_active_window: Callable[[], WindowSnapshot | None]) -> None:
        self._get_active_window = get_active_window
        self._current_window: WindowSnapshot | None = None
        self._focus_started_at: str | None = None

    @property
    def current_window(self) -> WindowSnapshot | None:
        return self._current_window

    def poll(self, timeline: Timeline) -> list[Event]:
        observed = self._get_active_window()
        events: list[Event] = []
        if observed is None:
            return events

        if self._current_window is None:
            event = timeline.create_event(
                "window.focus_started",
                "window",
                observed,
                {"window": observed.to_dict()},
            )
            self._current_window = observed
            self._focus_started_at = event.timestamp
            return [event]

        if self._is_different_window(observed, self._current_window):
            ended_at = timeline.now()
            ended = timeline.create_event(
                "window.focus_ended",
                "window",
                self._current_window,
                {
                    "window": self._current_window.to_dict(),
                    "started_at": self._focus_started_at,
                    "ended_at": ended_at,
                    "duration_ms": self._duration_ms(self._focus_started_at, ended_at),
                },
                timestamp=ended_at,
            )
            started = timeline.create_event(
                "window.focus_started",
                "window",
                observed,
                {"window": observed.to_dict()},
            )
            self._current_window = observed
            self._focus_started_at = started.timestamp
            return [ended, started]

        if observed.title != self._current_window.title:
            old_title = self._current_window.title
            self._current_window = observed
            return [
                timeline.create_event(
                    "window.title_changed",
                    "window",
                    observed,
                    {
                        "window": {
                            "process_name": observed.process_name,
                            "process_id": observed.process_id,
                            "handle": observed.handle,
                        },
                        "old_title": old_title,
                        "new_title": observed.title,
                    },
                )
            ]

        return events

    @staticmethod
    def _is_different_window(left: WindowSnapshot, right: WindowSnapshot) -> bool:
        return left.handle != right.handle or left.process_id != right.process_id

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
```

- [ ] **Step 4: Fix timestamp double-read before completing task**

Adjust the focus-change implementation so it calls the timeline clock once for the ended event. Replace the focus-change branch in `src/behavior_logger/collectors/window.py` with:

```python
        if self._is_different_window(observed, self._current_window):
            ended_at = timeline.now()
            ended = timeline.create_event(
                "window.focus_ended",
                "window",
                self._current_window,
                {
                    "window": self._current_window.to_dict(),
                    "started_at": self._focus_started_at,
                    "ended_at": ended_at,
                    "duration_ms": self._duration_ms(self._focus_started_at, ended_at),
                },
                timestamp=ended_at,
            )
            started = timeline.create_event(
                "window.focus_started",
                "window",
                observed,
                {"window": observed.to_dict()},
            )
            self._current_window = observed
            self._focus_started_at = started.timestamp
            return [ended, started]
```

- [ ] **Step 5: Run collector tests**

Run:

```powershell
python -m unittest tests.test_collectors -v
```

Expected: FAIL only because `IdleCollector` is still missing.

## Task 6: Idle Collector

**Files:**
- Create: `src/behavior_logger/collectors/idle.py`
- Test: `tests/test_collectors.py`

- [ ] **Step 1: Implement idle collector**

```python
# src/behavior_logger/collectors/idle.py
from __future__ import annotations

from collections.abc import Callable

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
            event = timeline.create_event(
                "idle.ended",
                "idle",
                active_window,
                {
                    "idle_started_at": self._idle_started_at,
                    "idle_ended_at": timeline.now(),
                    "duration_ms": 0,
                },
            )
            self._is_idle = False
            self._idle_started_at = None
            return [event]

        return []
```

- [ ] **Step 2: Improve idle duration calculation**

Update `src/behavior_logger/collectors/idle.py` to compute duration consistently:

```python
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
```

- [ ] **Step 3: Run collector tests**

Run:

```powershell
python -m unittest tests.test_collectors -v
```

Expected: PASS.

## Task 7: Windows API Adapter

**Files:**
- Create: `src/behavior_logger/windows_api.py`

- [ ] **Step 1: Implement standard-library Windows API adapter**

```python
# src/behavior_logger/windows_api.py
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import time

from .events import WindowSnapshot


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


def get_active_window() -> WindowSnapshot | None:
    handle = user32.GetForegroundWindow()
    if not handle:
        return None

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
    title = _get_window_title(handle)
    process_name = _get_process_name(process_id.value)

    return WindowSnapshot(
        handle=int(handle),
        process_id=int(process_id.value),
        process_name=process_name,
        title=title,
    )


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    millis = kernel32.GetTickCount() - info.dwTime
    return max(0.0, millis / 1000.0)


def _get_window_title(handle: int) -> str:
    length = user32.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


def _get_process_name(process_id: int) -> str:
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not process:
        return f"pid:{process_id}"
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name
        return f"pid:{process_id}"
    finally:
        kernel32.CloseHandle(process)
```

- [ ] **Step 2: Run import smoke test on Windows**

Run:

```powershell
python -c "from behavior_logger.windows_api import get_active_window, get_idle_seconds; print(get_active_window()); print(get_idle_seconds())"
```

Expected: Prints a `WindowSnapshot(...)` or `None`, then a floating-point idle second count.

## Task 8: Runner

**Files:**
- Create: `src/behavior_logger/runner.py`

- [ ] **Step 1: Implement runner loop**

```python
# src/behavior_logger/runner.py
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
```

- [ ] **Step 2: Add runner tests if runner behavior changes**

Run the full suite after Task 10. The runner is intentionally thin and depends on already-tested components.

## Task 9: Tail Formatting

**Files:**
- Create: `src/behavior_logger/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Write failing formatting tests**

```python
# tests/test_formatting.py
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_formatting -v
```

Expected: FAIL with missing `formatting`.

- [ ] **Step 3: Implement formatter**

```python
# src/behavior_logger/formatting.py
from __future__ import annotations

from datetime import datetime
from typing import Any


def format_event_line(event: dict[str, Any]) -> str:
    time_part = _time_part(event["timestamp"])
    event_type = event["type"]
    data = event.get("data", {})

    if event_type == "window.focus_started":
        window = data.get("window", {})
        return f"{time_part} {event_type} {window.get('process_name', '')} | {window.get('title', '')}"

    if event_type == "window.focus_ended":
        window = data.get("window", {})
        return f"{time_part} {event_type} {window.get('process_name', '')} | {data.get('duration_ms', 0)}ms"

    if event_type == "window.title_changed":
        return f"{time_part} {event_type} {data.get('old_title', '')} -> {data.get('new_title', '')}"

    if event_type == "idle.ended":
        return f"{time_part} {event_type} | {data.get('duration_ms', 0)}ms"

    return f"{time_part} {event_type}"


def _time_part(timestamp: str) -> str:
    try:
        return datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
    except ValueError:
        return timestamp[:8]
```

- [ ] **Step 4: Run formatting tests**

Run:

```powershell
python -m unittest tests.test_formatting -v
```

Expected: PASS.

## Task 10: CLI

**Files:**
- Create: `src/behavior_logger/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests for parser defaults**

```python
# tests/test_cli.py
import unittest

from behavior_logger.cli import build_parser


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_cli -v
```

Expected: FAIL with missing `cli`.

- [ ] **Step 3: Implement CLI**

```python
# src/behavior_logger/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .collectors.idle import IdleCollector
from .collectors.window import WindowCollector
from .formatting import format_event_line
from .runner import LoggerRunner
from .storage import EventStore
from .timeline import Timeline
from .windows_api import get_active_window, get_idle_seconds


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
    store = EventStore(Path(args.db))
    store.initialize()
    count = store.export_jsonl(args.out, type_filter=args.type)
    print(f"Exported {count} events to {args.out}")
    return 0
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
python -m unittest tests.test_cli -v
```

Expected: PASS.

## Task 11: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS for all tests.

- [ ] **Step 2: Run CLI help smoke test**

Run:

```powershell
python -m behavior_logger --help
```

Expected: Help output lists `run`, `tail`, and `export`.

- [ ] **Step 3: Run short manual collection smoke test**

Start the logger:

```powershell
python -m behavior_logger run --db data\behavior.db --poll-interval 1 --idle-threshold 60
```

Let it run for 5-10 seconds, switch between two windows, then press `Ctrl+C`.

Expected: Command exits cleanly after `Ctrl+C`.

- [ ] **Step 4: Inspect recent events**

Run:

```powershell
python -m behavior_logger tail --db data\behavior.db --limit 20
```

Expected: Output includes `recording.started`, one or more `window.focus_started` events, and `recording.stopped`. If a window switch happened, output includes `window.focus_ended`.

- [ ] **Step 5: Export JSONL**

Run:

```powershell
python -m behavior_logger export --db data\behavior.db --out exports\events.jsonl
```

Expected: Prints `Exported N events to exports\events.jsonl`, where `N` is greater than 0.

- [ ] **Step 6: Inspect JSONL file**

Run:

```powershell
Get-Content exports\events.jsonl -TotalCount 3
```

Expected: Each line is a complete JSON object with `id`, `timestamp`, `schema_version`, `type`, `source`, `session_id`, `sequence`, `context`, and `data`.

## Self-Review Notes

- Spec coverage: Phase 1 event model, SQLite storage, Windows foreground window logging, title change logging, idle transition logging, `run`, `tail`, and `export` are covered.
- Explicitly excluded: mouse/keyboard event logging, screenshots, OCR, privacy filtering, cloud sync, UI/tray app, and behavior analysis.
- The plan uses only Python standard library modules.
- The Windows API adapter is isolated so the collector tests do not require real Windows foreground-window state.
