"""Explicit, backup-first reset of one project into a fresh V2 runtime."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from novel_agent.state.schema_version import SCHEMA_VERSION, SchemaState, inspect_schema_state
from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_BACKUP_ROOTS = ("data", "state", "workspace")
_RESET_ROOTS = (
    "data",
    "state",
    "workspace",
    "logs",
    "dashboard",
    "exports",
    "dist",
    "build",
)
_EXCLUDED_PARTS = frozenset({"logs", "plugins", "__pycache__"})
_SENSITIVE_NAMES = frozenset(
    {
        ".env",
        "pipeline.yaml",
        "pipeline.yml",
        "models.json",
        "credentials.json",
        "secrets.json",
    }
)
_ACTIVE_STATUSES = ("pending", "claimed", "running", "paused")
_RESET_LOCK = threading.RLock()


class V2ResetError(RuntimeError):
    pass


class UnsafeProjectPathError(V2ResetError):
    pass


class ActiveProjectTasksError(V2ResetError):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    sha256: str
    size_bytes: int
    file_count: int
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "name": self.path.name,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ResetResult:
    backup: BackupResult
    schema_version: int
    cleared_roots: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "reset",
            "backup": self.backup.as_dict(),
            "schema_version": self.schema_version,
            "cleared_roots": list(self.cleared_roots),
        }


def _validated_project_path(
    projects_root: Path,
    project_root: Path,
    project_id: str,
) -> tuple[Path, Path]:
    if not _PROJECT_ID_RE.fullmatch(project_id) or ".." in project_id:
        raise UnsafeProjectPathError("Invalid project id")
    try:
        projects = Path(projects_root).resolve(strict=True)
        project = Path(project_root).resolve(strict=True)
    except OSError as exc:
        raise UnsafeProjectPathError("Project path does not exist") from exc
    if project.parent != projects or project.name != project_id:
        raise UnsafeProjectPathError(
            "Project must be an immediate child of the configured projects directory"
        )
    return projects, project


def _has_persisted_active_tasks(project_root: Path) -> bool:
    db_path = project_root / "data" / "novel.sqlite"
    if not db_path.is_file():
        return False
    connection: sqlite3.Connection | None = None
    try:
        uri = db_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        table = connection.execute(
            "select 1 from sqlite_master where type='table' and name='tasks'"
        ).fetchone()
        if not table:
            return False
        placeholders = ",".join("?" for _ in _ACTIVE_STATUSES)
        row = connection.execute(
            f"select 1 from tasks where status in ({placeholders}) limit 1",
            _ACTIVE_STATUSES,
        ).fetchone()
        return row is not None
    except sqlite3.DatabaseError as exc:
        raise V2ResetError(f"Task state could not be inspected: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()


def _ensure_idle(project_root: Path) -> None:
    if _has_persisted_active_tasks(project_root):
        raise ActiveProjectTasksError(
            "Project has active tasks; cancel or finish them before backup/reset"
        )


def _is_excluded(relative: Path) -> bool:
    lowered_parts = tuple(part.lower() for part in relative.parts)
    name = relative.name.lower()
    return (
        any(part in _EXCLUDED_PARTS for part in lowered_parts)
        or name in _SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.endswith(".log")
    )


def _iter_backup_files(project_root: Path) -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    candidates = [project_root / name for name in _BACKUP_ROOTS]

    for candidate in candidates:
        if not candidate.exists() or candidate.is_symlink():
            continue
        for current, directories, filenames in os.walk(candidate, followlinks=False):
            current_path = Path(current)
            directories[:] = [
                name
                for name in directories
                if not (current_path / name).is_symlink()
                and not _is_excluded(
                    (current_path / name).relative_to(project_root)
                )
            ]
            for filename in filenames:
                source = current_path / filename
                relative = source.relative_to(project_root)
                if source.is_symlink() or _is_excluded(relative):
                    continue
                if source.is_file():
                    files.append((source, relative))
    files.sort(key=lambda item: item[1].as_posix())
    return files


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_v2_backup(
    *,
    projects_root: Path,
    project_root: Path,
    project_id: str,
) -> BackupResult:
    """Create and verify a secrets-excluding archive without modifying the project."""

    projects, project = _validated_project_path(
        projects_root,
        project_root,
        project_id,
    )
    with _RESET_LOCK:
        _ensure_idle(project)
        created = datetime.now(UTC)
        backup_dir = projects.parent / "backups" / "v2-reset"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = created.strftime("%Y%m%dT%H%M%S%fZ")
        target = backup_dir / f"{project_id}-{stamp}.zip"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=backup_dir,
            prefix=f".{project_id}-",
            suffix=".tmp",
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        files = _iter_backup_files(project)
        manifest_files: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(
                temporary,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                for source, relative in files:
                    digest = _file_sha256(source)
                    size = source.stat().st_size
                    archive.write(source, relative.as_posix())
                    manifest_files.append(
                        {
                            "path": relative.as_posix(),
                            "size_bytes": size,
                            "sha256": digest,
                        }
                    )
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "format": "novel-agent-v2-backup",
                            "version": 1,
                            "project_id": project_id,
                            "created_at": created.isoformat(),
                            "files": manifest_files,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            with temporary.open("r+b") as stream:
                os.fsync(stream.fileno())
            with zipfile.ZipFile(temporary, mode="r") as archive:
                if archive.testzip() is not None:
                    raise V2ResetError("Backup archive failed CRC verification")
                manifest = json.loads(archive.read("manifest.json"))
                if manifest.get("project_id") != project_id:
                    raise V2ResetError("Backup manifest verification failed")
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return BackupResult(
            path=target,
            sha256=_file_sha256(target),
            size_bytes=target.stat().st_size,
            file_count=len(files),
            created_at=created.isoformat(),
        )


def _remove_checked(path: Path, *, parent: Path) -> None:
    resolved_parent = parent.resolve(strict=True)
    candidate_parent = path.parent.resolve(strict=True)
    if candidate_parent != resolved_parent:
        raise UnsafeProjectPathError(f"Refusing to remove path outside {resolved_parent}")
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def reset_project_to_v2(
    *,
    projects_root: Path,
    project_root: Path,
    project_id: str,
) -> ResetResult:
    """Back up, transactionally replace runtime roots, and initialize schema V2."""

    projects, project = _validated_project_path(
        projects_root,
        project_root,
        project_id,
    )
    with _RESET_LOCK:
        _ensure_idle(project)
        backup = create_v2_backup(
            projects_root=projects,
            project_root=project,
            project_id=project_id,
        )
        _ensure_idle(project)

        quarantine = projects / f".{project_id}.v2-reset-{uuid.uuid4().hex}"
        quarantine.mkdir()
        moved: list[str] = []
        fresh_roots: list[str] = []
        try:
            for name in _RESET_ROOTS:
                source = project / name
                if not source.exists() and not source.is_symlink():
                    continue
                destination = quarantine / name
                os.replace(source, destination)
                moved.append(name)

            for name in ("data", "state", "workspace", "logs", "dashboard"):
                (project / name).mkdir(parents=True, exist_ok=True)
                fresh_roots.append(name)
            (project / "workspace" / "chapters").mkdir(parents=True, exist_ok=True)
            SQLiteStateStore(project)
            state, version = inspect_schema_state(project / "data" / "novel.sqlite")
            if state is not SchemaState.V2 or version != SCHEMA_VERSION:
                raise V2ResetError("Fresh V2 schema verification failed")
        except Exception:
            for name in fresh_roots:
                fresh = project / name
                if fresh.exists() or fresh.is_symlink():
                    _remove_checked(fresh, parent=project)
            for name in reversed(moved):
                os.replace(quarantine / name, project / name)
            _remove_checked(quarantine, parent=projects)
            raise

        try:
            _remove_checked(quarantine, parent=projects)
        except OSError as exc:
            logger.warning("Reset succeeded but quarantine cleanup failed: %s", exc)
        return ResetResult(
            backup=backup,
            schema_version=SCHEMA_VERSION,
            cleared_roots=tuple(moved),
        )
