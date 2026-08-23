"""Operational endpoints for the optional M2 hybrid search projection."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from novel_agent.control.longform_flags import flag_enabled
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

router = APIRouter(tags=["search"])


@router.get("/api/search/status")
def get_search_status(session: ProjectSession = RequireProjectDep) -> dict:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    return {
        **store.fts5_status(),
        "enabled": flag_enabled("m2_hybrid_retrieval", session.root_dir),
    }


@router.post("/api/search/rebuild-index")
def rebuild_search_index(session: ProjectSession = RequireProjectDep) -> dict:
    session = coerce_project_session(session)
    return SQLiteStateStore(session.root_dir).rebuild_story_search_index()


@router.get("/api/search")
def search_story(
    query: str = Query(..., min_length=1, max_length=300),
    limit: int = Query(default=20, ge=1, le=200),
    before_chapter: str = Query(default="", max_length=64),
    session: ProjectSession = RequireProjectDep,
) -> dict:
    session = coerce_project_session(session)
    if not flag_enabled("m2_hybrid_retrieval", session.root_dir):
        raise HTTPException(
            503,
            "混合检索尚未启用；请打开 runtime.longform_flags.m2_hybrid_retrieval",
        )
    store = SQLiteStateStore(session.root_dir)
    return {
        "query": query,
        "results": store.search_story(
            query,
            limit=limit,
            before_chapter=before_chapter or None,
        ),
        "readiness": store.fts5_status(),
    }
