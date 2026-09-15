"""SQLite Storage repository for ShanShan Assistant data (threads, messages, patches, memories)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional
import uuid



from novel_agent.assistant.models import (
    AssistantPatch,
    AuthorPreference,
    CitationReference,
    EditorRange,
    PatchStatus,
    RunRecord,
    SourceType,
    ToolCallStep,
)


def _get_db_path(root_dir: Optional[Path]) -> Path:
    if root_dir and root_dir.is_dir():
        db_dir = root_dir / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "assistant.sqlite"
    # Fallback default local cache
    fallback = Path.home() / ".inkrest" / "assistant.sqlite"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


class AssistantStore:
    _lock = threading.Lock()

    def __init__(self, root_dir: Optional[Path]):
        self.root_dir = Path(root_dir) if root_dir else None
        self.db_path = _get_db_path(self.root_dir)
        self._init_tables()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass


    def _init_tables(self) -> None:
        with self._lock, self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS assistant_threads (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    archived INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS assistant_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    skill_id TEXT,
                    model_id TEXT,
                    references_json TEXT,
                    patch_id TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS assistant_patches (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    thread_id TEXT,
                    source_range_json TEXT,
                    original_text TEXT NOT NULL,
                    proposed_text TEXT NOT NULL,
                    reason TEXT,
                    skill_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS assistant_memories (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    project_id TEXT,
                    preference_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS assistant_runs (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    project_id TEXT,
                    skill_id TEXT,
                    model_id TEXT,
                    status TEXT NOT NULL,
                    steps_json TEXT,
                    output_text TEXT,
                    total_elapsed_ms INTEGER DEFAULT 0,
                    created_at TEXT
                );
                """
            )
            conn.commit()

    def save_patch(self, patch: AssistantPatch) -> None:
        now = datetime.now().isoformat()
        range_json = patch.source_range.model_dump_json() if patch.source_range else None
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assistant_patches (
                    id, project_id, chapter_id, thread_id, source_range_json,
                    original_text, proposed_text, reason, skill_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, coalesce(?, ?), ?)
                """,
                (
                    patch.id,
                    patch.project_id,
                    patch.chapter_id,
                    patch.thread_id,
                    range_json,
                    patch.original_text,
                    patch.proposed_text,
                    patch.reason,
                    patch.skill_id,
                    patch.status.value,
                    patch.created_at,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_patch(self, patch_id: str) -> Optional[AssistantPatch]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM assistant_patches WHERE id = ?", (patch_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_patch(row)

    def list_patches(
        self,
        project_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AssistantPatch]:
        query = "SELECT * FROM assistant_patches WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if chapter_id:
            query += " AND chapter_id = ?"
            params.append(chapter_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_patch(r) for r in rows]

    def update_patch_status(self, patch_id: str, status: PatchStatus) -> Optional[AssistantPatch]:
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "UPDATE assistant_patches SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, patch_id),
            )
            conn.commit()
        return self.get_patch(patch_id)

    def _row_to_patch(self, row: sqlite3.Row) -> AssistantPatch:
        source_range = None
        if row["source_range_json"]:
            try:
                data = json.loads(row["source_range_json"])
                source_range = EditorRange(**data)
            except Exception:
                pass
        return AssistantPatch(
            id=row["id"],
            project_id=row["project_id"],
            chapter_id=row["chapter_id"],
            thread_id=row["thread_id"],
            source_range=source_range,
            original_text=row["original_text"],
            proposed_text=row["proposed_text"],
            reason=row["reason"] or "",
            skill_id=row["skill_id"],
            status=PatchStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def save_preference(self, pref: AuthorPreference) -> AuthorPreference:
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assistant_memories (
                    id, scope, project_id, preference_type, content, created_at
                ) VALUES (?, ?, ?, ?, ?, coalesce(?, ?))
                """,
                (
                    pref.id,
                    pref.scope,
                    pref.project_id,
                    pref.preference_type,
                    pref.content,
                    pref.created_at,
                    now,
                ),
            )
            conn.commit()
        return pref

    def list_preferences(self, project_id: Optional[str] = None) -> List[AuthorPreference]:
        """Returns global preferences plus project-scoped preferences."""
        with self._lock, self._get_conn() as conn:
            if project_id:
                rows = conn.execute(
                    """
                    SELECT * FROM assistant_memories
                    WHERE scope = 'global' OR project_id = ?
                    ORDER BY created_at ASC
                    """,
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM assistant_memories WHERE scope = 'global' ORDER BY created_at ASC"
                ).fetchall()

            return [
                AuthorPreference(
                    id=r["id"],
                    scope=r["scope"],
                    project_id=r["project_id"],
                    preference_type=r["preference_type"],
                    content=r["content"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def delete_preference(self, pref_id: str) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.execute("DELETE FROM assistant_memories WHERE id = ?", (pref_id,))
            conn.commit()
            return cur.rowcount > 0

    def save_run(self, run: RunRecord) -> None:
        steps_json = json.dumps([s.model_dump() for s in run.steps], ensure_ascii=False)
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assistant_runs (
                    id, thread_id, project_id, skill_id, model_id,
                    status, steps_json, output_text, total_elapsed_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, coalesce(?, datetime('now')))
                """,
                (
                    run.id,
                    run.thread_id,
                    run.project_id,
                    run.skill_id,
                    run.model_id,
                    run.status,
                    steps_json,
                    run.output_text,
                    run.total_elapsed_ms,
                    run.created_at,
                ),
            )
            conn.commit()

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT * FROM assistant_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def list_runs(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RunRecord]:
        query = "SELECT * FROM assistant_runs WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_run(r) for r in rows]

    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        steps: List[ToolCallStep] = []
        if row["steps_json"]:
            try:
                raw_steps = json.loads(row["steps_json"])
                steps = [ToolCallStep(**s) for s in raw_steps]
            except Exception:
                pass
        return RunRecord(
            id=row["id"],
            thread_id=row["thread_id"],
            project_id=row["project_id"],
            skill_id=row["skill_id"],
            model_id=row["model_id"],
            status=row["status"],
            steps=steps,
            output_text=row["output_text"] or "",
            total_elapsed_ms=row["total_elapsed_ms"] or 0,
            created_at=row["created_at"],
        )

    def create_thread(
        self,
        title: str = "新对话",
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = thread_id or f"thread_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assistant_threads (
                    id, project_id, title, created_at, updated_at, archived
                ) VALUES (?, ?, ?, coalesce(?, ?), ?, 0)
                """,
                (tid, project_id, title, now, now, now),
            )
            conn.commit()
        return {
            "id": tid,
            "project_id": project_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "archived": 0,
        }

    def list_threads(
        self,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM assistant_threads WHERE archived = 0"
        params: List[Any] = []
        if project_id:
            query += " AND (project_id = ? OR project_id IS NULL)"
            params.append(project_id)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            row = conn.execute("SELECT * FROM assistant_threads WHERE id = ?", (thread_id,)).fetchone()
            return dict(row) if row else None

    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        skill_id: Optional[str] = None,
        model_id: Optional[str] = None,
        references_json: Optional[str] = None,
        patch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        mid = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO assistant_messages (
                    id, thread_id, role, content, skill_id, model_id, references_json, patch_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mid, thread_id, role, content, skill_id, model_id, references_json, patch_id, now),
            )
            conn.execute("UPDATE assistant_threads SET updated_at = ? WHERE id = ?", (now, thread_id))
            conn.commit()
        return {
            "id": mid,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "skill_id": skill_id,
            "model_id": model_id,
            "references_json": references_json,
            "patch_id": patch_id,
            "created_at": now,
        }

    def list_messages(self, thread_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM assistant_messages WHERE thread_id = ? ORDER BY created_at ASC LIMIT ?",
                (thread_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]


