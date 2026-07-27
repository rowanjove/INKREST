"""V2 manuscript center routes."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from novel_agent.domain.manuscript import (
    ManuscriptDocument,
    ManuscriptRevision,
    ManuscriptWorkspace,
)
from novel_agent.services.manuscript_workspace import (
    build_manuscript_workspace,
    restore_manuscript_revision,
    save_manuscript_document,
)
from novel_agent.state.manuscript_repository import DocumentConflictError
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.deps import (
    ProjectSession,
    RequireProjectDep,
    coerce_project_session,
    touch_project_activity,
)
from web.helpers import _validate_id

router = APIRouter()


class SaveManuscriptRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content_json: Dict[str, Any]
    expected_revision: int = Field(..., ge=1)
    source: str = Field(default="autosave", pattern=r"^(autosave|manual|ai_accept)$")


class RestoreManuscriptRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)


def _conflict_response(exc: DocumentConflictError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "DOCUMENT_CONFLICT",
            "message": "正文已在其他窗口更新，请选择要保留的版本。",
            "current": exc.current,
        },
    )


@router.get("/api/manuscript/workspace", response_model=ManuscriptWorkspace)
def get_manuscript_workspace(
    chapter_id: str = Query(default=""),
    query: str = Query(default="", max_length=120),
    status: str = Query(default="all", pattern=r"^(all|draft|ready|attention)$"),
    session: ProjectSession = RequireProjectDep,
) -> ManuscriptWorkspace:
    session = coerce_project_session(session)
    if chapter_id:
        _validate_id(chapter_id, "chapter_id")
    return build_manuscript_workspace(
        session.root_dir,
        chapter_id=chapter_id,
        query=query,
        status=status,
    )


@router.put(
    "/api/manuscript/documents/{chapter_id}",
    response_model=ManuscriptDocument,
)
def put_manuscript_document(
    chapter_id: str,
    req: SaveManuscriptRequest,
    session: ProjectSession = RequireProjectDep,
) -> ManuscriptDocument:
    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    try:
        document = save_manuscript_document(
            session.root_dir,
            chapter_id=safe_id,
            title=req.title,
            content_json=req.content_json,
            expected_revision=req.expected_revision,
            source=req.source,
        )
    except DocumentConflictError as exc:
        raise _conflict_response(exc)
    except KeyError:
        raise HTTPException(404, "章节不存在")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    touch_project_activity(session)
    return ManuscriptDocument(**document)


@router.get(
    "/api/manuscript/documents/{chapter_id}/revisions",
    response_model=List[ManuscriptRevision],
)
def get_manuscript_revisions(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> List[ManuscriptRevision]:
    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    store = SQLiteStateStore(session.root_dir)
    return [
        ManuscriptRevision(**row)
        for row in store.list_manuscript_revisions(safe_id, limit=100)
    ]


@router.post(
    "/api/manuscript/documents/{chapter_id}/revisions/{revision_id}/restore",
    response_model=ManuscriptDocument,
)
def post_restore_manuscript_revision(
    chapter_id: str,
    revision_id: str,
    req: RestoreManuscriptRequest,
    session: ProjectSession = RequireProjectDep,
) -> ManuscriptDocument:
    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    try:
        document = restore_manuscript_revision(
            session.root_dir,
            chapter_id=safe_id,
            revision_id=revision_id,
            expected_revision=req.expected_revision,
        )
    except DocumentConflictError as exc:
        raise _conflict_response(exc)
    except KeyError:
        raise HTTPException(404, "正文历史不存在")
    touch_project_activity(session)
    return ManuscriptDocument(**document)
