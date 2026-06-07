"""Test-only fixtures for Playwright E2E (disabled unless E2E_FIXTURES=1)."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

import web.context as ctx
from web.e2e_seed import seed_maintenance_scenario
from web.helpers import _ensure_dirs
from web.tasks import TaskManager

router = APIRouter(tags=["e2e-fixtures"])


def _fixtures_enabled() -> bool:
    return os.environ.get("E2E_FIXTURES", "").strip() in ("1", "true", "yes")


@router.post("/api/e2e/seed-maintenance-scenario")
def post_seed_maintenance_scenario() -> Dict[str, Any]:
    if not _fixtures_enabled():
        raise HTTPException(404, "E2E fixtures are disabled")
    with ctx._project_lock:
        payload = seed_maintenance_scenario(ctx.project_manager)
        pid = payload["project_id"]
        ctx.project_manager.switch_project(pid)
        ctx._active_project_id = pid
        ctx._task_manager = TaskManager(ctx.get_root_dir())
        _ensure_dirs(ctx.get_root_dir())
    return payload