"""Incremental Change Journal and Tombstone Engine (Milestone F).

Maintains a monotonic sequence of all data mutations, enabling delta-based
conflict-free synchronization without uploading monolithic SQLite databases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class JournalEntry:
    seq: int
    entity_type: str
    entity_id: str
    operation: OperationType
    revision: int
    device_id: str
    timestamp: str
    payload_json: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "operation": self.operation.value,
            "revision": self.revision,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "payload": json.loads(self.payload_json) if self.payload_json else None,
        }


class ChangeJournal:
    """SQLite-backed monotonic change journal for an INKREST Vault."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                create table if not exists change_journal (
                    seq integer primary key autoincrement,
                    entity_type text not null,
                    entity_id text not null,
                    operation text not null,
                    revision integer not null,
                    device_id text not null,
                    timestamp text not null,
                    payload_json text
                )
                """
            )
            conn.execute(
                "create index if not exists idx_journal_entity on change_journal(entity_type, entity_id)"
            )
            conn.commit()
        finally:
            conn.close()

    def record_change(
        self,
        entity_type: str,
        entity_id: str,
        operation: OperationType,
        revision: int,
        device_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> JournalEntry:
        """Record an insertion, mutation, or deletion."""
        payload_str = json.dumps(payload, ensure_ascii=False) if payload else None
        ts = now_iso()
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                """
                insert into change_journal
                (entity_type, entity_id, operation, revision, device_id, timestamp, payload_json)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (entity_type, entity_id, operation.value, revision, device_id, ts, payload_str),
            )
            seq = cur.lastrowid
            conn.commit()
            return JournalEntry(
                seq=seq,
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                revision=revision,
                device_id=device_id,
                timestamp=ts,
                payload_json=payload_str,
            )
        finally:
            conn.close()

    def record_tombstone(
        self,
        entity_type: str,
        entity_id: str,
        revision: int,
        device_id: str,
    ) -> JournalEntry:
        """Record a tombstone for a deleted entity so that remote sync nodes delete it too."""
        return self.record_change(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=OperationType.DELETE,
            revision=revision,
            device_id=device_id,
            payload=None,
        )

    def get_changes_after(self, last_seq: int, limit: int = 500) -> List[JournalEntry]:
        """Fetch delta mutations occurring after last_seq."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                """
                select seq, entity_type, entity_id, operation, revision, device_id, timestamp, payload_json
                from change_journal
                where seq > ?
                order by seq asc
                limit ?
                """,
                (last_seq, limit),
            )
            rows = cur.fetchall()
            return [
                JournalEntry(
                    seq=r[0],
                    entity_type=r[1],
                    entity_id=r[2],
                    operation=OperationType(r[3]),
                    revision=r[4],
                    device_id=r[5],
                    timestamp=r[6],
                    payload_json=r[7],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_latest_seq(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("select max(seq) from change_journal").fetchone()
            return row[0] or 0
        finally:
            conn.close()
