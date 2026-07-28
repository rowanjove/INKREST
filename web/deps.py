"""FastAPI dependencies for project-scoped request context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request

import web.context as ctx
from web.context import get_root_dir, require_project_root

ACTOR_HEADER = "X-Novel-Agent-Actor"


@dataclass(frozen=True)
class ProjectSession:
    """Read-only view of the active project for a single request."""

    project_id: Optional[str]
    root_dir: Path
    actor_id: str = "local"

    @property
    def has_project(self) -> bool:
        return bool(self.project_id)


def _resolve_actor_id(request: Request) -> str:
    raw = str(request.headers.get(ACTOR_HEADER) or "").strip()
    if not raw:
        return "local"
    return raw[:64]


def coerce_project_session(session: Any = None) -> ProjectSession:
    """Resolve session for direct handler calls (unit tests) or FastAPI injection."""
    if isinstance(session, ProjectSession):
        return session
    return ProjectSession(
        project_id=ctx._active_project_id,
        root_dir=get_root_dir(),
        actor_id="local",
    )


def get_project_session(request: Request) -> ProjectSession:
    return ProjectSession(
        project_id=ctx._active_project_id,
        root_dir=get_root_dir(),
        actor_id=_resolve_actor_id(request),
    )


def require_project_session(request: Request) -> ProjectSession:
    root = require_project_root()
    return ProjectSession(
        project_id=ctx._active_project_id,
        root_dir=root,
        actor_id=_resolve_actor_id(request),
    )


def touch_project_activity(session: ProjectSession) -> None:
    """Record last activity for the active project when present."""
    if session.project_id:
        ctx.project_manager.touch_activity(session.project_id)


def task_manager_for(session: ProjectSession):
    """Return the task manager bound to this request's captured project root."""
    captured_root = Path(session.root_dir).resolve()
    if captured_root == Path(get_root_dir()).resolve():
        return ctx._get_task_manager()
    return ctx._task_registry.get(captured_root)


def current_project_info(session: ProjectSession) -> Dict[str, Any]:
    """Resolve {id, name} for the active project (or nulls when none)."""
    if not session.project_id:
        return {"id": None, "name": None}
    data = ctx.project_manager._read_registry()
    info = data.get("projects", {}).get(session.project_id, {})
    if not info:
        return {"id": None, "name": None}
    name = info.get("name", session.project_id)
    return {"id": session.project_id, "name": name}


# Typed aliases for route signatures
ProjectSessionDep = Depends(get_project_session)
RequireProjectDep = Depends(require_project_session)
