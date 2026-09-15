"""Shared application context and state for the Novel Agent web service."""

import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional
from fastapi import HTTPException
from web.project_task_registry import ProjectTaskRegistry
from web.tasks import TaskManager

# ---- Base directory (where projects.json and projects/ live) ----
if os.environ.get("NOVEL_AGENT_ROOT"):
    BASE_DIR = Path(os.environ["NOVEL_AGENT_ROOT"]).resolve()
elif getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# ---- Active project tracking ----
_active_project_id: Optional[str] = None
_task_manager: Optional[TaskManager] = None  # optional test override
_task_registry = ProjectTaskRegistry.shared()
_project_lock = threading.RLock()

# Lazy load managers to prevent circular imports during module loading
def __getattr__(name: str):
    if name == "project_manager":
        from web.project_manager import ProjectManager
        return ProjectManager(BASE_DIR)
    if name == "preset_manager":
        from web.preset_manager import PresetManager
        return PresetManager(BASE_DIR)
    import web.helpers as ws_helpers
    if hasattr(ws_helpers, name):
        return getattr(ws_helpers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_root_dir() -> Path:
    """Return the active project directory, falling back to BASE_DIR for legacy mode."""
    if _active_project_id:
        return BASE_DIR / "projects" / _active_project_id
    return BASE_DIR


def require_project_root() -> Path:
    """Active or legacy project root; raises 400 when no book is open."""
    if _active_project_id:
        root = BASE_DIR / "projects" / _active_project_id
        if not root.is_dir():
            raise HTTPException(404, "当前项目不存在，请从书库重新打开。")
        if (root / "workspace").is_dir() or (root / "config" / "pipeline.yaml").is_file():
            return root
        raise HTTPException(400, "请先在书库选择并打开一本书。")
    # App workspace with a book library must not fall back to the repo root.
    if (BASE_DIR / "projects").is_dir() or (BASE_DIR / "projects.json").is_file():
        raise HTTPException(400, "请先在书库选择并打开一本书。")
    return BASE_DIR


def _get_task_manager() -> TaskManager:
    if _task_manager is not None:
        return _task_manager
    return _task_registry.get(get_root_dir())


def get_project_store(project_id: str):
    """Return a state store bound to the requested project, not the active project."""
    projects_dir = (BASE_DIR / "projects").resolve()
    project_dir = (projects_dir / project_id).resolve()
    if projects_dir not in project_dir.parents:
        raise HTTPException(400, "Invalid project_id: path traversal detected")
    if not project_dir.exists() or not project_dir.is_dir():
        raise HTTPException(404, f"Project {project_id} not found")
    from novel_agent.state.sqlite_store import SQLiteStateStore
    return SQLiteStateStore(project_dir)


def _has_active_tasks() -> bool:
    root = get_root_dir()
    if _task_manager is not None:
        if not Path(_task_manager.root_dir).exists():
            return False
        return _task_manager.has_active_tasks()
    if not root.exists():
        return False
    return _task_registry.has_active_tasks(root)


def _ensure_no_active_tasks(action: str) -> None:
    if _has_active_tasks():
        raise HTTPException(409, f"Cannot {action} while generation tasks are running")


def reset_plugin_manager() -> None:
    """Release plugin resources when switching projects."""
    global _plugin_manager
    if _plugin_manager is not None:
        _plugin_manager.shutdown()
        _plugin_manager = None


def activate_project(project_id: str) -> None:
    """Sync in-memory active project, task manager, and plugin scope."""
    global _active_project_id, _task_manager
    from web.helpers import _ensure_dirs, _init_prompt_defaults

    with _project_lock:
        _active_project_id = project_id
        root = get_root_dir()
        if not root.is_dir():
            _active_project_id = None
            raise HTTPException(404, "当前项目目录不存在，请从书库重新打开或导入。")
        _task_manager = None
        _task_registry.get(root)
        _ensure_dirs(root)
        _init_prompt_defaults(root)
        reset_plugin_manager()


def release_project(project_id: str) -> None:
    """Release project-scoped resources before deleting its directory."""
    global _active_project_id, _task_manager

    root = BASE_DIR / "projects" / project_id
    with _project_lock:
        _task_registry.drop(root)
        if _active_project_id == project_id:
            reset_plugin_manager()
            _active_project_id = None
            _task_manager = None


_plugin_manager: Optional[Any] = None
_global_plugin_manager: Optional[Any] = None


def get_global_plugin_manager() -> Any:
    """App-level plugin manager (BASE_DIR/plugins). Survives project switches."""
    global _global_plugin_manager
    if _global_plugin_manager is None or _global_plugin_manager.root_dir != BASE_DIR:
        from novel_agent.plugins import PluginManager

        if _global_plugin_manager is not None:
            _global_plugin_manager.shutdown()
        _global_plugin_manager = PluginManager(BASE_DIR, allow_web_extensions=True)
        _global_plugin_manager.initialize()
    return _global_plugin_manager


def get_plugin_manager() -> Any:
    """Project plugin manager when a book is open; otherwise the global manager."""
    global _plugin_manager
    if not _active_project_id:
        return get_global_plugin_manager()
    root_dir = get_root_dir()
    if _plugin_manager is None or _plugin_manager.root_dir != root_dir:
        from novel_agent.plugins import PluginManager

        if _plugin_manager is not None:
            _plugin_manager.shutdown()
        _plugin_manager = PluginManager(root_dir, allow_web_extensions=False)
        _plugin_manager.initialize()
    return _plugin_manager


def resolve_plugin_manager(plugin_id: str) -> Any:
    """Prefer the project manager, then the surviving global manager."""
    project_pm = get_plugin_manager()
    if plugin_id in getattr(project_pm, "plugins", {}):
        return project_pm
    global_pm = get_global_plugin_manager()
    if plugin_id in getattr(global_pm, "plugins", {}):
        return global_pm
    return project_pm


def merged_plugin_catalog() -> list:
    global_cat = get_global_plugin_manager().list_plugin_catalog()
    if not _active_project_id:
        return global_cat
    by_name = {item.get("name"): item for item in global_cat}
    for item in get_plugin_manager().list_plugin_catalog():
        name = item.get("name")
        existing = by_name.get(name)
        if existing and existing.get("plugin_type") == "web_extension":
            continue
        by_name[name] = item
    return [item for item in by_name.values() if item]


def merged_plugin_navigation() -> dict:
    global_nav = get_global_plugin_manager().get_navigation_contributions()
    if not _active_project_id:
        return global_nav
    project_nav = get_plugin_manager().get_navigation_contributions()
    merged = {
        "library_sidebar": list(global_nav.get("library_sidebar") or []),
        "project_sidebar": list(global_nav.get("project_sidebar") or []),
    }
    seen_lib = {item.get("id") for item in merged["library_sidebar"]}
    seen_proj = {item.get("id") for item in merged["project_sidebar"]}
    for item in project_nav.get("library_sidebar") or []:
        if item.get("id") not in seen_lib:
            merged["library_sidebar"].append(item)
            seen_lib.add(item.get("id"))
    for item in project_nav.get("project_sidebar") or []:
        if item.get("id") not in seen_proj:
            merged["project_sidebar"].append(item)
            seen_proj.add(item.get("id"))
    return merged


def merged_plugin_frontends() -> dict:
    """Return a safe, static frontend manifest derived from trusted navigation data."""
    navigation = merged_plugin_navigation()
    pages_by_plugin: dict[str, dict] = {}
    for surface, items in navigation.items():
        for item in items or []:
            plugin_id = str(item.get("plugin_id") or "")
            view_id = str(item.get("view") or "")
            if not plugin_id or not view_id:
                continue
            record = pages_by_plugin.setdefault(
                plugin_id,
                {
                    "plugin_id": plugin_id,
                    "name": item.get("plugin_name") or plugin_id,
                    "scope": "global" if surface == "library_sidebar" else "project",
                    "icon": item.get("icon") or "extensions",
                    "pages": [],
                },
            )
            record["pages"].append(
                {
                    "id": view_id,
                    "title": item.get("title") or view_id,
                    "surface": surface,
                    "path": item.get("path"),
                    "entry": f"/api/plugins/{plugin_id}/views/{view_id}/document",
                }
            )
    return {"plugins": list(pages_by_plugin.values())}
