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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_root_dir() -> Path:
    """Return the active project directory, falling back to BASE_DIR for legacy mode."""
    if _active_project_id:
        return BASE_DIR / "projects" / _active_project_id
    return BASE_DIR


def require_project_root() -> Path:
    """Active or legacy project root; raises 400 when no book is open."""
    root = get_root_dir()
    if _active_project_id:
        if not root.is_dir():
            raise HTTPException(404, "当前项目不存在，请从书库重新打开。")
        return root
    if (root / "workspace").is_dir() or (root / "projects").is_dir():
        return root
    raise HTTPException(400, "请先在书库选择并打开一本书。")


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
        _task_manager = None
        _task_registry.get(root)
        _ensure_dirs(root)
        _init_prompt_defaults(root)
        reset_plugin_manager()


_plugin_manager: Optional[Any] = None


def get_plugin_manager() -> Any:
    """Get the PluginManager for the active project, lazy-initialized."""
    global _plugin_manager
    root_dir = get_root_dir()
    if _plugin_manager is None or _plugin_manager.root_dir != root_dir:
        from novel_agent.plugins import PluginManager
        if _plugin_manager is not None:
            _plugin_manager.shutdown()
        _plugin_manager = PluginManager(root_dir, allow_web_extensions=root_dir == BASE_DIR)
        _plugin_manager.initialize()
    return _plugin_manager
