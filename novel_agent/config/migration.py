"""Non-destructive pipeline configuration migration inspection and apply.

Opening an old project only inspects its raw YAML.  Applying a migration
requires an exact confirmation token and always creates a byte-for-byte backup
before writing the new validated document.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from .io import write_pipeline_document
from .schema import CONFIG_SCHEMA_VERSION


@dataclass(frozen=True)
class ConfigMigrationPlan:
    path: str
    current_version: int
    target_version: int
    needs_migration: bool
    safe_changes: tuple[str, ...]
    backup_required: bool = True
    confirmation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _raw(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def inspect_config_migration(path: Path) -> ConfigMigrationPlan:
    target = Path(path)
    raw = _raw(target)
    try:
        version = int(raw.get("schema_version") or 0)
    except (TypeError, ValueError):
        version = 0
    changes: list[str] = []
    if version < CONFIG_SCHEMA_VERSION:
        changes.append(f"schema_version {version} → {CONFIG_SCHEMA_VERSION}")
    if "max_workers" in raw:
        changes.append("move top-level max_workers into runtime")
    if "retry_attempts" in raw:
        changes.append("move top-level retry_attempts into runtime")
    if "target_chars" in raw and "chapter" not in raw:
        changes.append("move top-level target_chars into chapter.default_target_chars")
    token = f"MIGRATE {target.name}"
    return ConfigMigrationPlan(str(target), version, CONFIG_SCHEMA_VERSION, bool(changes), tuple(changes), True, token)


def migration_status(root_dir: Path) -> dict[str, Any]:
    path = Path(root_dir) / "config" / "pipeline.yaml"
    plan = inspect_config_migration(path)
    return {"status": "required" if plan.needs_migration else "current", "plan": plan.to_dict()}


def _migrated_document(raw: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(raw))
    runtime = dict(document.get("runtime") or {}) if isinstance(document.get("runtime"), Mapping) else {}
    chapter = dict(document.get("chapter") or {}) if isinstance(document.get("chapter"), Mapping) else {}
    for key in ("max_workers", "retry_attempts"):
        if key in document and key not in runtime:
            runtime[key] = document[key]
        document.pop(key, None)
    if "target_chars" in document and "default_target_chars" not in chapter:
        value = document.get("target_chars")
        chapter["default_target_chars"] = value if isinstance(value, list) else [1200, 2200]
        document.pop("target_chars", None)
    document["runtime"] = runtime
    document["chapter"] = chapter
    document.setdefault("quality", {})
    document.setdefault("llm", {"provider": "static"})
    document.setdefault("embedding", {"provider": "stub"})
    document["schema_version"] = CONFIG_SCHEMA_VERSION
    return document


def apply_config_migration(path: Path, *, confirmation: str, backup_dir: Path | None = None) -> dict[str, Any]:
    target = Path(path)
    plan = inspect_config_migration(target)
    if not plan.needs_migration:
        return {"status": "current", "plan": plan.to_dict(), "backup": None}
    if str(confirmation or "") != plan.confirmation:
        raise ValueError(f"explicit confirmation required: {plan.confirmation}")
    if not target.is_file():
        raise FileNotFoundError(str(target))
    data = target.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:16]
    folder = Path(backup_dir) if backup_dir else target.parent / ".migration-backups"
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / f"{target.stem}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{digest}.bak"
    shutil.copy2(target, backup)
    migrated = _migrated_document(_raw(target))
    write_pipeline_document(target, migrated)
    return {"status": "migrated", "plan": inspect_config_migration(target).to_dict(), "backup": str(backup)}


__all__ = ["ConfigMigrationPlan", "apply_config_migration", "inspect_config_migration", "migration_status"]
