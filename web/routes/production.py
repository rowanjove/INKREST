"""Unified production-center API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from novel_agent.services.production_workspace import build_production_workspace
from novel_agent.services.quality_review import build_quality_review_queue
from web.deps import ProjectSession, RequireProjectDep, current_project_info

router = APIRouter(tags=["production"])


@router.get("/api/production/workspace")
def get_production_workspace(
    session: ProjectSession = RequireProjectDep,
    task_limit: int = Query(100, ge=1, le=500),
    event_limit: int = Query(300, ge=1, le=500),
    log_limit: int = Query(300, ge=1, le=500),
) -> dict[str, Any]:
    return build_production_workspace(
        session.root_dir,
        project_id=session.project_id or session.root_dir.name,
        project_info=current_project_info(session),
        task_limit=task_limit,
        event_limit=event_limit,
        log_limit=log_limit,
    ).model_dump(mode="json")


@router.get("/api/production/reviews")
def get_production_reviews(
    session: ProjectSession = RequireProjectDep,
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    severity: str | None = Query(None),
    stage: str | None = Query(None),
) -> dict[str, Any]:
    return build_quality_review_queue(
        session.root_dir,
        cursor=cursor,
        limit=limit,
        severity_filter=severity,
        status_filter=stage,
    )
