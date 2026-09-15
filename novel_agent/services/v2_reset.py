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
_DELETE_BACKUP_EXCLUDED_PARTS = frozenset(
    {"logs", "__pycache__", "build", "dist", "dist-desktop", "node_modules"}
)
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
MAX_BACKUP_FILES = 20000
MAX_BACKUP_FILE_BYTES = 512 * 1024 * 1024
MAX_BACKUP_TOTAL_BYTES = 8 * 1024 * 1024 * 1024


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


def _is_excluded(
    relative: Path,
    *,
    excluded_parts: frozenset[str] = _EXCLUDED_PARTS,
) -> bool:
    lowered_parts = tuple(part.lower() for part in relative.parts)
    name = relative.name.lower()
    return (
        any(part in excluded_parts for part in lowered_parts)
        or name in _SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.endswith(".log")
    )


def _iter_backup_files(
    project_root: Path,
    *,
    include_all: bool = False,
) -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    candidates = [project_root] if include_all else [project_root / name for name in _BACKUP_ROOTS]
    excluded_parts = _DELETE_BACKUP_EXCLUDED_PARTS if include_all else _EXCLUDED_PARTS

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
                    (current_path / name).relative_to(project_root),
                    excluded_parts=excluded_parts,
                )
            ]
            for filename in filenames:
                source = current_path / filename
                relative = source.relative_to(project_root)
                if source.is_symlink() or _is_excluded(
                    relative,
                    excluded_parts=excluded_parts,
                ):
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


def _write_backup_member(
    archive: zipfile.ZipFile,
    source: Path,
    relative: Path,
) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as input_stream, archive.open(
        relative.as_posix(),
        mode="w",
    ) as output_stream:
        for chunk in iter(lambda: input_stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
            output_stream.write(chunk)
    return {
        "path": relative.as_posix(),
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def _snapshot_sqlite_database(source: Path, destination: Path) -> None:
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    try:
        source_connection = sqlite3.connect(
            source.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=30,
        )
        destination_connection = sqlite3.connect(destination)
        source_connection.backup(destination_connection)
    finally:
        if destination_connection is not None:
            destination_connection.close()
        if source_connection is not None:
            source_connection.close()


def _verify_backup_manifest(
    archive: zipfile.ZipFile,
    manifest: dict[str, Any],
    *,
    project_id: str,
) -> None:
    if manifest.get("project_id") != project_id:
        raise V2ResetError("Backup manifest verification failed")
    for item in manifest.get("files") or []:
        path = str(item.get("path") or "")
        digest = hashlib.sha256()
        size = 0
        try:
            with archive.open(path, mode="r") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
        except KeyError as exc:
            raise V2ResetError(f"Backup member missing: {path}") from exc
        try:
            expected_size = int(item["size_bytes"])
        except (KeyError, TypeError, ValueError) as exc:
            raise V2ResetError(f"Backup member size missing: {path}") from exc
        if size != expected_size:
            raise V2ResetError(f"Backup member size mismatch: {path}")
        if digest.hexdigest() != str(item.get("sha256") or ""):
            raise V2ResetError(f"Backup member hash mismatch: {path}")


def list_backup_inventory(
    project_root: Path,
    *,
    include_all: bool = False,
) -> dict[str, Any]:
    """Stream-friendly backup inventory with explicit size/file caps."""

    files = _iter_backup_files(Path(project_root), include_all=include_all)
    total_bytes = 0
    oversized: list[str] = []
    for source, relative in files:
        size = int(source.stat().st_size)
        total_bytes += size
        if size > MAX_BACKUP_FILE_BYTES:
            oversized.append(relative.as_posix())
    if len(files) > MAX_BACKUP_FILES:
        raise V2ResetError(
            f"Backup file count {len(files)} exceeds {MAX_BACKUP_FILES}"
        )
    if oversized:
        raise V2ResetError(
            f"Backup file exceeds {MAX_BACKUP_FILE_BYTES} bytes: {oversized[0]}"
        )
    if total_bytes > MAX_BACKUP_TOTAL_BYTES:
        raise V2ResetError(
            f"Backup total size {total_bytes} exceeds {MAX_BACKUP_TOTAL_BYTES} bytes"
        )
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "max_files": MAX_BACKUP_FILES,
        "max_file_bytes": MAX_BACKUP_FILE_BYTES,
        "max_total_bytes": MAX_BACKUP_TOTAL_BYTES,
    }


def _create_verified_backup(
    *,
    projects_root: Path,
    project_root: Path,
    project_id: str,
    include_all: bool,
    backup_namespace: str,
    manifest_format: str,
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
        backup_dir = projects.parent / "backups" / backup_namespace
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = created.strftime("%Y%m%dT%H%M%S%fZ")
        target = backup_dir / f"{project_id}-{stamp}.zip"
        files = _iter_backup_files(project, include_all=include_all)
        list_backup_inventory(project, include_all=include_all)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=backup_dir,
            prefix=f".{project_id}-",
            suffix=".tmp",
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        sqlite_relative = Path("data") / "novel.sqlite"
        sqlite_snapshot = temporary.with_suffix(".sqlite")
        sqlite_source = project / sqlite_relative
        manifest_files: list[dict[str, Any]] = []
        try:
            if sqlite_source.is_file():
                _snapshot_sqlite_database(sqlite_source, sqlite_snapshot)
                files = [
                    (source, relative)
                    for source, relative in files
                    if relative
                    not in {
                        sqlite_relative,
                        Path("data") / "novel.sqlite-wal",
                        Path("data") / "novel.sqlite-shm",
                    }
                ]
                files.append((sqlite_snapshot, sqlite_relative))
                files.sort(key=lambda item: item[1].as_posix())
            with zipfile.ZipFile(
                temporary,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                for source, relative in files:
                    manifest_files.append(
                        _write_backup_member(archive, source, relative)
                    )
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "format": manifest_format,
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
                _verify_backup_manifest(
                    archive,
                    manifest,
                    project_id=project_id,
                )
            os.replace(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            sqlite_snapshot.unlink(missing_ok=True)
        return BackupResult(
            path=target,
            sha256=_file_sha256(target),
            size_bytes=target.stat().st_size,
            file_count=len(files),
            created_at=created.isoformat(),
        )


def create_v2_backup(
    *,
    projects_root: Path,
    project_root: Path,
    project_id: str,
) -> BackupResult:
    """Back up reset-owned runtime roots before a V2 reset."""
    return _create_verified_backup(
        projects_root=projects_root,
        project_root=project_root,
        project_id=project_id,
        include_all=False,
        backup_namespace="v2-reset",
        manifest_format="novel-agent-v2-backup",
    )


def create_project_deletion_backup(
    *,
    projects_root: Path,
    project_root: Path,
    project_id: str,
) -> BackupResult:
    """Back up all recoverable project data before deleting the project."""
    return _create_verified_backup(
        projects_root=projects_root,
        project_root=project_root,
        project_id=project_id,
        include_all=True,
        backup_namespace="project-delete",
        manifest_format="novel-agent-project-deletion-backup",
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
