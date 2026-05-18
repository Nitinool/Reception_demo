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
