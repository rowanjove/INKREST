"""Offline + registry helpers for AI agents (CLI / MCP / skills)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

_DEFAULT_BASE: Optional[Path] = None


def default_base_dir() -> Path:
    global _DEFAULT_BASE
    if _DEFAULT_BASE is not None:
        return _DEFAULT_BASE
    env = os.environ.get("NOVEL_AGENT_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    try:
        import web.context as ctx

        return Path(ctx.BASE_DIR).resolve()
    except Exception:
        return Path(__file__).resolve().parents[2]


def set_default_base_dir(path: Path) -> None:
    global _DEFAULT_BASE
    _DEFAULT_BASE = Path(path).resolve()


def list_projects(base_dir: Optional[Path] = None) -> Dict[str, Any]:
    base = Path(base_dir or default_base_dir())
    reg_path = base / "projects.json"
    if not reg_path.is_file():
        return {"projects": [], "active_id": None, "base_dir": str(base)}
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"projects": [], "active_id": None, "base_dir": str(base)}
    projects = []
    for pid, meta in (data.get("projects") or {}).items():
        if not isinstance(meta, dict):
            continue
        projects.append(
            {
                "id": pid,
                "name": meta.get("name") or pid,
                "description": meta.get("description") or "",
                "target_chapters": meta.get("target_chapters"),
            }
        )
    return {
        "base_dir": str(base),
        "active_id": data.get("active_id"),
        "projects": sorted(projects, key=lambda p: p.get("name") or ""),
    }


def validate_project_id(project_id: str) -> str:
    """Reject path traversal in project_id (CLI / MCP / offline agents)."""
    if not project_id or not _PROJECT_ID_RE.match(project_id):
        raise ValueError(
            "Invalid project_id: must contain only alphanumeric, underscore, hyphen"
        )
    if ".." in project_id or "/" in project_id or "\\" in project_id:
        raise ValueError("Invalid project_id: path traversal detected")
    return project_id


def resolve_project_root(
    base_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Path:
    base = Path(base_dir or default_base_dir())
    if project_id:
        safe_id = validate_project_id(project_id)
        projects_root = (base / "projects").resolve()
        root = (projects_root / safe_id).resolve()
        try:
            root.relative_to(projects_root)
        except ValueError as exc:
            raise ValueError("Invalid project_id: escapes projects directory") from exc
        if not root.is_dir():
            raise FileNotFoundError(f"Project directory not found: {root}")
        return root
    reg = list_projects(base)
    active = reg.get("active_id")
    if not active:
        raise ValueError(
            "No active project. Pass --project-id or set active project in the UI."
        )
    return resolve_project_root(base, str(active))


def tail_project_logs(
    root_dir: Path,
    *,
    max_lines: int = 80,
    include_global: bool = True,
) -> Dict[str, Any]:
    lines: List[str] = []
    paths: Dict[str, str] = {}
    proj_log = root_dir / "logs" / "novel_agent.log"
    if proj_log.is_file():
        paths["project"] = str(proj_log)
        lines.extend(_read_log_tail(proj_log, max_lines))
    if include_global:
        global_log = default_base_dir() / "logs" / "novel_agent.log"
        if global_log.is_file() and str(global_log) not in paths.values():
            paths["global"] = str(global_log)
            if not lines:
                lines.extend(_read_log_tail(global_log, max_lines))
    return {"paths": paths, "lines": lines[-max_lines:]}


def _read_log_tail(path: Path, max_lines: int) -> List[str]:
    try:
        from web.runtime_log_buffer import read_system_log_tail

        return read_system_log_tail(path, max_lines)
    except Exception:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return text.splitlines()[-max_lines:]
        except OSError:
            return []


def build_agent_snapshot(
    root_dir: Path,
    *,
    project_id: str = "",
) -> Dict[str, Any]:
    """Return the same canonical project state consumed by the product UI."""
    from novel_agent.services.project_snapshot import build_project_snapshot

    resolved_id = project_id or Path(root_dir).name
    project_info: Dict[str, Any] = {}
    registry = list_projects(default_base_dir())
    for item in registry.get("projects", []):
        if item.get("id") == resolved_id:
            project_info = item
            break
    return build_project_snapshot(
        root_dir,
        project_id=resolved_id,
        project_info=project_info,
    ).model_dump(mode="json")
