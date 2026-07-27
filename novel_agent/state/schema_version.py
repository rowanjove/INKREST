"""V2 SQLite schema detection without silently upgrading legacy user data."""

from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path


SCHEMA_VERSION = 2


class SchemaState(str, Enum):
    FRESH = "fresh"
    V2 = "v2"
    LEGACY = "legacy"


class LegacySchemaError(RuntimeError):
    """Raised when a V2-only operation targets unversioned legacy data."""


def inspect_schema_state(db_path: Path) -> tuple[SchemaState, int | None]:
    path = Path(db_path)
    if not path.is_file() or path.stat().st_size == 0:
        return SchemaState.FRESH, None
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path)
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
            if not str(row[0]).startswith("sqlite_")
        }
        if not tables:
            return SchemaState.FRESH, None
        if "app_metadata" not in tables:
            # A new project may have an auxiliary vector/arc table before the
            # unified store is opened. The unversioned legacy task table is the
            # reliable evidence that user data predates V2.
            if "tasks" in tables:
                return SchemaState.LEGACY, None
            return SchemaState.FRESH, None
        row = conn.execute(
            "select value from app_metadata where key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return SchemaState.LEGACY, None
    finally:
        if conn is not None:
            conn.close()
    if not row:
        return SchemaState.LEGACY, None
    try:
        version = int(row[0])
    except (TypeError, ValueError):
        return SchemaState.LEGACY, None
    if version == SCHEMA_VERSION:
        return SchemaState.V2, version
    return SchemaState.LEGACY, version


def write_schema_version(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            create table if not exists app_metadata (
              key text primary key,
              value text not null
            )
            """
        )
        conn.execute(
            """
            insert into app_metadata (key, value) values ('schema_version', ?)
            on conflict(key) do update set value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
    finally:
        conn.close()
