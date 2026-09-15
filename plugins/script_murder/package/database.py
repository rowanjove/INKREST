"""Isolated SQLite storage manager for Script Murder projects."""

from __future__ import annotations

import json
import re
import sqlite3
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import (
    CharacterProfile,
    ClueItem,
    DeductiveConclusion,
    GameFlow,
    ProjectMeta,
    ScriptMurderWorkspace,
    TruthCanon,
    GenerationTaskRecord,
)


PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class _ClosingConnection(sqlite3.Connection):
    """sqlite's context manager commits but does not close; close on scope exit."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class DatabaseManager:
    """Manages project catalogs and per-project isolated SQLite databases."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root).resolve()
        self.base_dir = self.data_root / "data" / "plugins" / "script_murder"
        self.projects_dir = self.base_dir / "projects"
        self.trash_dir = self.base_dir / "trash"
        self.catalog_db_path = self.base_dir / "projects.sqlite"
        self._ensure_dirs()
        self._init_catalog_db()

    def _ensure_dirs(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_project_id(project_id: str) -> str:
        value = str(project_id or "").strip()
        if not PROJECT_ID_RE.fullmatch(value):
            raise ValueError("Invalid project_id")
        return value

    def _get_catalog_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.catalog_db_path), factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_catalog_db(self) -> None:
        with self._get_catalog_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_catalog (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    player_count INTEGER NOT NULL DEFAULT 6,
                    duration_minutes INTEGER NOT NULL DEFAULT 240,
                    genre_json TEXT NOT NULL DEFAULT '[]',
                    era TEXT NOT NULL DEFAULT '',
                    setting TEXT NOT NULL DEFAULT '',
                    difficulty INTEGER NOT NULL DEFAULT 4,
                    status TEXT NOT NULL DEFAULT 'planning',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    node TEXT NOT NULL,
                    status TEXT NOT NULL,
                    apply_state TEXT NOT NULL DEFAULT 'applied',
                    input_revision INTEGER NOT NULL DEFAULT 1,
                    dependency_hash TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT 'offline',
                    prompt_version TEXT NOT NULL DEFAULT '1',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(generation_tasks)").fetchall()}
            if "apply_state" not in columns:
                conn.execute("ALTER TABLE generation_tasks ADD COLUMN apply_state TEXT NOT NULL DEFAULT 'applied'")
            conn.commit()

    def _get_project_db_path(self, project_id: str) -> Path:
        project_id = self.validate_project_id(project_id)
        proj_dir = self.projects_dir / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir / "project.sqlite"

    def _get_project_conn(self, project_id: str) -> sqlite3.Connection:
        project_id = self.validate_project_id(project_id)
        db_path = self._get_project_db_path(project_id)
        conn = sqlite3.connect(str(db_path), factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_project_db(self, project_id: str) -> None:
        project_id = self.validate_project_id(project_id)
        with self._get_project_conn(project_id) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_state (
                    key TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    full_dump_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # -----------------------------------------------------------------------
    # Catalog Operations
    # -----------------------------------------------------------------------

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._get_catalog_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM project_catalog ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["genre"] = json.loads(item.get("genre_json") or "[]")
                del item["genre_json"]
                results.append(item)
            return results

    def create_project(self, meta: ProjectMeta) -> ScriptMurderWorkspace:
        self.validate_project_id(meta.id)
        now = time.time()
        meta.created_at = now
        meta.updated_at = now

        with self._get_catalog_conn() as conn:
            if conn.execute("SELECT 1 FROM project_catalog WHERE id = ?", (meta.id,)).fetchone():
                raise ValueError(f"Project '{meta.id}' already exists")
            conn.execute(
                """
                INSERT INTO project_catalog (
                    id, title, player_count, duration_minutes, genre_json,
                    era, setting, difficulty, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meta.id,
                    meta.title,
                    meta.player_count,
                    meta.duration_minutes,
                    json.dumps(meta.genre, ensure_ascii=False),
                    meta.era,
                    meta.setting,
                    meta.difficulty,
                    meta.status,
                    meta.created_at,
                    meta.updated_at,
                ),
            )
            conn.commit()

        self._init_project_db(meta.id)
        workspace = ScriptMurderWorkspace(meta=meta)
        self.save_workspace(workspace)
        return workspace

    def delete_project(self, project_id: str) -> bool:
        project_id = self.validate_project_id(project_id)
        proj_dir = self.projects_dir / project_id
        if not proj_dir.is_dir():
            return False
        trash_target = self.trash_dir / f"{project_id}-{int(time.time() * 1000)}"
        # Move first so a failed filesystem operation never loses catalog state.
        try:
            shutil.move(str(proj_dir), str(trash_target))
        except OSError:
            return False
        with self._get_catalog_conn() as conn:
            cursor = conn.execute("DELETE FROM project_catalog WHERE id = ?", (project_id,))
            conn.commit()
            if cursor.rowcount == 0:
                try:
                    shutil.move(str(trash_target), str(proj_dir))
                except OSError:
                    pass
                return False
        return True

    def list_deleted_projects(self) -> List[Dict[str, Any]]:
        """List recoverable project directories in the plugin trash area."""
        results: List[Dict[str, Any]] = []
        for entry in sorted(self.trash_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not entry.is_dir() or "-" not in entry.name:
                continue
            project_id, _, stamp = entry.name.rpartition("-")
            try:
                self.validate_project_id(project_id)
            except ValueError:
                continue
            results.append({"id": project_id, "trash_id": entry.name, "deleted_at": entry.stat().st_mtime})
        return results

    def restore_deleted_project(self, trash_id: str) -> Optional[str]:
        """Restore one exact trash entry without accepting path components."""
        value = str(trash_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,96}", value):
            raise ValueError("Invalid trash_id")
        source = self.trash_dir / value
        if not source.is_dir():
            return None
        project_id = value.rsplit("-", 1)[0]
        self.validate_project_id(project_id)
        target = self.projects_dir / project_id
        if target.exists():
            raise ValueError(f"Project '{project_id}' already exists")
        shutil.move(str(source), str(target))
        self._init_project_db(project_id)
        with self._get_project_conn(project_id) as conn:
            row = conn.execute("SELECT data_json FROM project_state WHERE key = 'meta'").fetchone()
        if not row:
            shutil.move(str(target), str(source))
            raise ValueError("Trash entry does not contain a valid project")
        meta = ProjectMeta.model_validate_json(row["data_json"])
        with self._get_catalog_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO project_catalog
                (id,title,player_count,duration_minutes,genre_json,era,setting,difficulty,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (meta.id, meta.title, meta.player_count, meta.duration_minutes,
                 json.dumps(meta.genre, ensure_ascii=False), meta.era, meta.setting,
                 meta.difficulty, meta.status, meta.created_at, time.time()),
            )
            conn.commit()
        return project_id

    # -----------------------------------------------------------------------
    # Workspace Load & Save
    # -----------------------------------------------------------------------

    def load_workspace(self, project_id: str) -> Optional[ScriptMurderWorkspace]:
        project_id = self.validate_project_id(project_id)
        with self._get_catalog_conn() as cat_conn:
            cursor = cat_conn.execute("SELECT id FROM project_catalog WHERE id = ?", (project_id,))
            if not cursor.fetchone():
                return None

        db_path = self._get_project_db_path(project_id)
        if not db_path.exists():
            return None

        self._init_project_db(project_id)
        with self._get_project_conn(project_id) as conn:
            cursor = conn.execute("SELECT key, data_json FROM project_state")
            rows = dict(cursor.fetchall())

        if "meta" not in rows:
            return None

        meta_dict = json.loads(rows["meta"])
        canon_dict = json.loads(rows.get("canon") or "{}")
        characters_list = json.loads(rows.get("characters") or "[]")
        clues_list = json.loads(rows.get("clues") or "[]")
        conclusions_list = json.loads(rows.get("conclusions") or "[]")
        flow_dict = json.loads(rows.get("flow") or "{}")
        host_guide = rows.get("host_guide") or ""
        brief = json.loads(rows.get("brief") or "{}")
        documents = json.loads(rows.get("documents") or "{}")
        artifact_status = json.loads(rows.get("artifact_status") or "{}")
        revisions = json.loads(rows.get("revisions") or "{}")
        dependency_hashes = json.loads(rows.get("dependency_hashes") or "{}")

        return ScriptMurderWorkspace(
            meta=ProjectMeta.model_validate(meta_dict),
            brief=brief,
            canon=TruthCanon.model_validate(canon_dict) if canon_dict else TruthCanon(),
            characters=[CharacterProfile.model_validate(c) for c in characters_list],
            clues=[ClueItem.model_validate(cl) for cl in clues_list],
            conclusions=[DeductiveConclusion.model_validate(cn) for cn in conclusions_list],
            flow=GameFlow.model_validate(flow_dict) if flow_dict else GameFlow(),
            host_guide=host_guide,
            documents=documents,
            revision=int(rows.get("revision") or 1),
            revisions=revisions or ScriptMurderWorkspace.model_fields["revisions"].default_factory(),
            artifact_status=artifact_status or ScriptMurderWorkspace.model_fields["artifact_status"].default_factory(),
            dependency_hashes=dependency_hashes,
        )

    def save_workspace(self, workspace: ScriptMurderWorkspace) -> None:
        self.validate_project_id(workspace.meta.id)
        project_id = workspace.meta.id
        now = time.time()
        workspace.meta.updated_at = now

        # Update catalog row
        with self._get_catalog_conn() as conn:
            conn.execute(
                """
                UPDATE project_catalog SET
                    title = ?,
                    player_count = ?,
                    duration_minutes = ?,
                    genre_json = ?,
                    era = ?,
                    setting = ?,
                    difficulty = ?,
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    workspace.meta.title,
                    workspace.meta.player_count,
                    workspace.meta.duration_minutes,
                    json.dumps(workspace.meta.genre, ensure_ascii=False),
                    workspace.meta.era,
                    workspace.meta.setting,
                    workspace.meta.difficulty,
                    workspace.meta.status,
                    now,
                    project_id,
                ),
            )
            conn.commit()

        # Update per-project states
        self._init_project_db(project_id)
        states = {
            "meta": workspace.meta.model_dump_json(),
            "canon": workspace.canon.model_dump_json(),
            "characters": json.dumps([c.model_dump() for c in workspace.characters], ensure_ascii=False),
            "clues": json.dumps([cl.model_dump() for cl in workspace.clues], ensure_ascii=False),
            "conclusions": json.dumps([cn.model_dump() for cn in workspace.conclusions], ensure_ascii=False),
            "flow": workspace.flow.model_dump_json(),
            "host_guide": workspace.host_guide,
            "brief": json.dumps(workspace.brief, ensure_ascii=False),
            "documents": json.dumps(workspace.documents, ensure_ascii=False),
            "revision": str(workspace.revision),
            "revisions": json.dumps(workspace.revisions, ensure_ascii=False),
            "artifact_status": json.dumps(workspace.artifact_status, ensure_ascii=False),
            "dependency_hashes": json.dumps(workspace.dependency_hashes, ensure_ascii=False),
        }

        with self._get_project_conn(project_id) as conn:
            for k, v in states.items():
                conn.execute(
                    "INSERT OR REPLACE INTO project_state (key, data_json, updated_at) VALUES (?, ?, ?)",
                    (k, v, now),
                )
            conn.commit()

    # -----------------------------------------------------------------------
    # Snapshot & Rollback
    # -----------------------------------------------------------------------

    def create_snapshot(self, project_id: str, label: str = "手动快照") -> str:
        project_id = self.validate_project_id(project_id)
        workspace = self.load_workspace(project_id)
        if not workspace:
            raise ValueError(f"Project '{project_id}' not found")

        snapshot_id = f"snap_{uuid.uuid4().hex}_{project_id[:6]}"
        dump_json = workspace.model_dump_json()

        with self._get_project_conn(project_id) as conn:
            conn.execute(
                "INSERT INTO snapshots (snapshot_id, label, created_at, full_dump_json) VALUES (?, ?, ?, ?)",
                (snapshot_id, label, time.time(), dump_json),
            )
            conn.commit()
        return snapshot_id

    def list_snapshots(self, project_id: str) -> List[Dict[str, Any]]:
        project_id = self.validate_project_id(project_id)
        self._init_project_db(project_id)
        with self._get_project_conn(project_id) as conn:
            cursor = conn.execute(
                "SELECT snapshot_id, label, created_at FROM snapshots ORDER BY created_at DESC LIMIT 50"
            )
            return [dict(r) for r in cursor.fetchall()]

    def restore_snapshot(self, project_id: str, snapshot_id: str) -> ScriptMurderWorkspace:
        project_id = self.validate_project_id(project_id)
        self._init_project_db(project_id)
        with self._get_project_conn(project_id) as conn:
            cursor = conn.execute(
                "SELECT full_dump_json FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Snapshot '{snapshot_id}' not found")
            raw_json = row["full_dump_json"]

        workspace = ScriptMurderWorkspace.model_validate_json(raw_json)
        self.save_workspace(workspace)
        return workspace

    # -----------------------------------------------------------------------
    # Persisted generation tasks
    # -----------------------------------------------------------------------

    def save_task(self, task: GenerationTaskRecord) -> None:
        self.validate_project_id(task.project_id)
        with self._get_catalog_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO generation_tasks
                (id, project_id, node, status, apply_state, input_revision, dependency_hash, model,
                 prompt_version, result_json, error, created_at, started_at, finished_at,
                 cancel_requested)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id, task.project_id, task.node, task.status, task.apply_state,
                    task.input_revision, task.dependency_hash, task.model,
                    task.prompt_version, json.dumps(task.result, ensure_ascii=False),
                    task.error, task.created_at, task.started_at, task.finished_at,
                    int(task.cancel_requested),
                ),
            )
            conn.commit()

    def get_task(self, task_id: str) -> Optional[GenerationTaskRecord]:
        with self._get_catalog_conn() as conn:
            row = conn.execute(
                "SELECT * FROM generation_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["result"] = json.loads(item.pop("result_json") or "{}")
        item["cancel_requested"] = bool(item.get("cancel_requested"))
        return GenerationTaskRecord.model_validate(item)

    def list_tasks(self, project_id: str, limit: int = 100) -> List[GenerationTaskRecord]:
        self.validate_project_id(project_id)
        with self._get_catalog_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM generation_tasks WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, max(1, min(int(limit), 500))),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["result"] = json.loads(item.pop("result_json") or "{}")
            item["cancel_requested"] = bool(item.get("cancel_requested"))
            results.append(GenerationTaskRecord.model_validate(item))
        return results
