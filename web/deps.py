"""FastAPI dependencies for project-scoped request context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException

import web.context as ctx
from web.context import get_root_dir, require_project_root


@dataclass(frozen=True)
class ProjectSession:
    """Read-only view of the active project for a single request."""

    project_id: Optional[str]
    root_dir: Path

    @property
    def has_project(self) -> bool:
        return bool(self.project_id)


def get_project_session() -> ProjectSession:
    return ProjectSession(project_id=ctx._active_project_id, root_dir=get_root_dir())


def require_project_session() -> ProjectSession:
    root = require_project_root()
    return ProjectSession(project_id=ctx._active_project_id, root_dir=root)


# Typed aliases for route signatures
ProjectSessionDep = Depends(get_project_session)
RequireProjectDep = Depends(require_project_session)