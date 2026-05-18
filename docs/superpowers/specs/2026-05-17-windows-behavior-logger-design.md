# Windows Behavior Logger Design

Date: 2026-05-17
Status: Draft for review

## Goal

Build a local Windows desktop behavior logger that records objective system-level activity, similar to a system log. The first version focuses on observable desktop state, not subjective user notes or behavioral interpretation.

The logger runs as a Python CLI program, stores events locally in SQLite, and provides commands to run collection, inspect recent events, and export raw logs.

## Non-Goals

- No cloud sync or upload.
- No behavior analysis, task inference, productivity scoring, or summaries.
- No mouse or keyboard event logging.
- No screenshot or OCR collection in the first version.
- No sensitive-window filtering in the first version.
- No graphical UI or tray application in the first version.

## First Version Scope

The first version records:

- When recording starts and stops.
- Which Windows foreground window gains focus.
- When a focused window loses focus, including focus duration.
- When the title of the focused window changes.
- When the system enters and exits idle state.

The first version includes three CLI commands:

- `python -m behavior_logger run`
- `python -m behavior_logger tail`
- `python -m behavior_logger export`

## Architecture

The program is split into five modules.

### Window Collector

Polls the current Windows foreground window on a fixed interval. It reads:

- Window handle.
- Process ID.
- Process name.
- Window title.

It detects:

- Focus started.
- Focus ended.
- Title changed.

### Idle Collector

Uses the Windows last-input timestamp to determine whether the user is idle. It does not record keyboard or mouse events. It only records transitions:

- Active to idle.
- Idle to active.

The default idle threshold is 60 seconds.

### Timeline

Normalizes collector observations into standard event objects. It is responsible for:

- Assigning event IDs.
- Assigning session-local sequence numbers.
- Adding timestamps.
- Adding shared context.
- Producing a stable event format for storage and export.

### Storage

Stores events in a local SQLite database. The first version uses a simple append-only event table.

Default database path during the prototype phase:

```text
.\data\behavior.db
```

### CLI Controller

Provides command-line entry points for running and inspecting the logger.

## Event Format

All events use the same outer structure:

```json
{
  "id": "evt_01HX...",
  "timestamp": "2026-05-17T17:40:12.123+08:00",
  "schema_version": 1,
  "type": "window.focus_started",
  "source": "window",
  "session_id": "run_20260517_174000",
  "sequence": 128,
  "context": {
    "active_window": {
      "process_name": "Code.exe",
      "process_id": 1234,
      "title": "main.py - behavior logger",
      "handle": 123456
    }
  },
  "data": {}
}
```

Field meanings:

- `id`: Globally unique event ID.
- `timestamp`: Event timestamp in ISO 8601 format with timezone.
- `schema_version`: Event schema version.
- `type`: Dot-separated event type.
- `source`: Producing subsystem.
- `session_id`: Current logger run.
- `sequence`: Monotonic event number within the session.
- `context`: Shared environment at event time.
- `data`: Event-specific payload.

The first version only uses `context.active_window`.

## Event Types

First version event types:

```text
recording.started
recording.stopped

window.focus_started
window.focus_ended
window.title_changed

idle.started
idle.ended
```

Reserved future event types:

```text
window.closed
privacy.skipped
screenshot.captured
ocr.completed
```

## Event Payloads

### `recording.started`

```json
{
  "config": {
    "poll_interval_seconds": 1.0,
    "idle_threshold_seconds": 60
  }
}
```

### `recording.stopped`

```json
{
  "reason": "user_interrupt"
}
```

### `window.focus_started`

```json
{
  "window": {
    "process_name": "Code.exe",
    "process_id": 1234,
    "title": "main.py - behavior logger",
    "handle": 123456
  }
}
```

### `window.focus_ended`

```json
{
  "window": {
    "process_name": "Code.exe",
    "process_id": 1234,
    "title": "main.py - behavior logger",
    "handle": 123456
  },
  "started_at": "2026-05-17T17:40:12.123+08:00",
  "ended_at": "2026-05-17T17:43:20.456+08:00",
  "duration_ms": 188333
}
```

### `window.title_changed`

```json
{
  "window": {
    "process_name": "Chrome.exe",
    "process_id": 2345,
    "handle": 888888
  },
  "old_title": "ChatGPT",
  "new_title": "ChatGPT - behavior logger discussion"
}
```

### `idle.started`

```json
{
  "idle_threshold_seconds": 60,
  "last_input_age_seconds": 60.2
}
```

### `idle.ended`

```json
{
  "idle_started_at": "2026-05-17T17:55:12.000+08:00",
  "idle_ended_at": "2026-05-17T17:56:20.000+08:00",
  "duration_ms": 68000
}
```

## SQLite Schema

The first version stores complete events in one append-only table:

```sql
CREATE TABLE events (
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
```

Indexes:

```sql
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_session_id ON events(session_id);
CREATE UNIQUE INDEX idx_events_session_sequence ON events(session_id, sequence);
```

## CLI Design

### `run`

Starts the logger and writes events to SQLite.

```powershell
python -m behavior_logger run
```

Options:

```text
--db .\data\behavior.db
--poll-interval 1.0
--idle-threshold 60
```

### `tail`

Shows recent events in a compact readable format.

```powershell
python -m behavior_logger tail
```

Options:

```text
--db .\data\behavior.db
--limit 50
--type window.focus_started
```

Example output:

```text
17:52:01 recording.started
17:52:03 window.focus_started Code.exe | main.py
17:54:10 window.focus_ended Code.exe | 127000ms
17:54:11 window.focus_started Chrome.exe | ChatGPT
17:55:12 idle.started
17:56:20 idle.ended | 68000ms
```

### `export`

Exports events as JSONL.

```powershell
python -m behavior_logger export --out .\exports\events.jsonl
```

Options:

```text
--db .\data\behavior.db
--out .\exports\events.jsonl
--type window.focus_started
```

## Implementation Notes

- Use Python for the prototype.
- Use SQLite from the Python standard library.
- Use Windows APIs through `pywin32` or `ctypes`.
- Poll the foreground window every 1 second by default.
- Use Windows `GetLastInputInfo` for idle detection.
- Keep storage local to the project during the prototype phase.

## Phase Plan

### Phase 1

Implement the Python CLI, event model, SQLite storage, window focus logging, title change logging, idle transition logging, `tail`, and `export`.

### Phase 2

Add optional screenshot capture with local file storage and screenshot events.

### Phase 3

Add OCR events associated with screenshots.

### Phase 4

Add privacy controls, including pause/resume, sensitive process rules, retention settings, and data deletion tools.

## Open Decisions

No implementation-blocking decisions remain for Phase 1.
