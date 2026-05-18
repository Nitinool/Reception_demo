from __future__ import annotations

from pathlib import Path
from contextlib import closing
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
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.executescript(SCHEMA)

    def insert(self, event: Event) -> None:
        record = event.to_record()
        with closing(sqlite3.connect(self.db_path)) as connection:
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
            connection.commit()

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

        with closing(sqlite3.connect(self.db_path)) as connection:
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
        with closing(sqlite3.connect(self.db_path)) as connection, output.open(
            "w", encoding="utf-8"
        ) as file:
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
