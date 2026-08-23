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
    apply_plain_text_to_manuscript,
    build_quality_candidate_diff,
    build_manuscript_workspace,
    load_quality_rewrite_candidate,
    mark_quality_rewrite_candidate_adopted,
    restore_manuscript_revision,
    save_manuscript_document,
    text_sha256,
)
from novel_agent.quality.candidate_set import (
    build_candidate_set,
    create_pairwise_session,
    list_candidate_feedback,
    list_candidate_timeline,
    load_candidate_set,
    rank_candidates,
    record_candidate_feedback,
    restore_candidate_set_snapshot,
    submit_pairwise_session,
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


class AcceptQualityCandidateRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)


class CandidateSetRequest(BaseModel):
    """Explicitly submit already-produced candidates for local review.

    The route never creates candidates itself; callers must provide the text
    and an optional CONTENT_LOCK payload.  ``expected_revision`` prevents a
    set from silently being attached to a newer manuscript revision.
    """

    expected_revision: int = Field(..., ge=1)
    candidates: List[Dict[str, Any]] = Field(default_factory=list, max_length=3)
    content_lock: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False
    cost_budget: int = Field(default=3, ge=1, le=100)
    ttl_days: int = Field(default=7, ge=1, le=90)


class CandidateFeedbackRequest(BaseModel):
    feedback: Dict[str, Any]


class CandidateSetRollbackRequest(BaseModel):
    timeline_id: str = Field(..., min_length=1, max_length=200)
    expected_candidate_set_id: str = Field(..., min_length=1, max_length=200)


class CandidateAdoptRequest(BaseModel):
    expected_revision: int = Field(..., ge=1)
    expected_candidate_set_id: str = Field(..., min_length=1, max_length=200)


class CandidatePairwiseRequest(BaseModel):
    expected_candidate_set_id: str = Field(..., min_length=1, max_length=200)
    candidate_a: str = Field(..., min_length=1, max_length=200)
    candidate_b: str = Field(..., min_length=1, max_length=200)


class CandidatePairwiseFeedbackRequest(BaseModel):
    choice: str = Field(..., pattern=r"^(a|b|tie|neither)$")


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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
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
        offset=offset,
        limit=limit,
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


@router.get("/api/manuscript/documents/{chapter_id}/quality-candidate")
def get_quality_candidate(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Return the isolated quality candidate and a bounded diff."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    candidate = load_quality_rewrite_candidate(session.root_dir, safe_id)
    if not candidate or not str(candidate.get("candidate_text") or "").strip():
        raise HTTPException(404, "暂无可审阅的返工候选稿")
    current = build_manuscript_workspace(session.root_dir, chapter_id=safe_id).document
    current_text = current.plain_text if current else ""
    return {
        "available": True,
        "chapter_id": safe_id,
        "current_revision": int(current.revision) if current else 0,
        "current_sha256": text_sha256(current_text),
        "candidate_text": candidate["candidate_text"],
        "metadata": candidate.get("metadata") or {},
        "artifact": candidate.get("artifact"),
        "diff": build_quality_candidate_diff(current_text, candidate["candidate_text"]),
    }


@router.post("/api/manuscript/documents/{chapter_id}/quality-candidate/accept")
def accept_quality_candidate(
    chapter_id: str,
    req: AcceptQualityCandidateRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Adopt a validated candidate as a new manual manuscript revision."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    candidate = load_quality_rewrite_candidate(session.root_dir, safe_id)
    candidate_text = str((candidate or {}).get("candidate_text") or "")
    metadata = dict((candidate or {}).get("metadata") or {})
    if not candidate or not candidate_text.strip():
        raise HTTPException(404, "暂无可采纳的返工候选稿")
    if metadata.get("status") == "rejected" or metadata.get("accepted") is not True:
        raise HTTPException(409, {"code": "QUALITY_CANDIDATE_REJECTED", "message": "候选稿未通过本地安全校验"})

    current = build_manuscript_workspace(session.root_dir, chapter_id=safe_id).document
    if current is None:
        raise HTTPException(404, "正文不存在")
    if int(current.revision) != int(req.expected_revision):
        raise HTTPException(
            409,
            {
                "code": "DOCUMENT_CONFLICT",
                "message": "正文已在其他窗口更新，请刷新后重试。",
                "current": current.model_dump(),
            },
        )
    source_sha = str(metadata.get("source_sha256") or "")
    if source_sha and source_sha != text_sha256(current.plain_text):
        raise HTTPException(
            409,
            {
                "code": "QUALITY_CANDIDATE_STALE",
                "message": "候选稿基于旧正文生成，请重新运行审校后再采纳。",
                "current_revision": int(current.revision),
            },
        )
    if text_sha256(candidate_text) == text_sha256(current.plain_text):
        adopted = mark_quality_rewrite_candidate_adopted(
            session.root_dir, safe_id, revision=int(current.revision), source="manual"
        )
        return {"status": "already_applied", "document": current.model_dump(), "metadata": adopted}

    try:
        document = apply_plain_text_to_manuscript(
            session.root_dir,
            chapter_id=safe_id,
            plain_text=candidate_text,
            title=current.title,
            expected_revision=int(req.expected_revision),
            source="manual",
        )
    except DocumentConflictError as exc:
        raise _conflict_response(exc) from exc
    adopted = mark_quality_rewrite_candidate_adopted(
        session.root_dir, safe_id, revision=int(document["revision"]), source="manual"
    )
    touch_project_activity(session)
    return {"status": "accepted", "document": document, "metadata": adopted}


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set")
def post_candidate_set(
    chapter_id: str,
    req: CandidateSetRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Persist an explicit bounded candidate set for human review.

    This is intentionally a storage/review boundary, not a generation route:
    no model or pipeline call is made here.
    """

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    current = build_manuscript_workspace(session.root_dir, chapter_id=safe_id).document
    if current is None:
        raise HTTPException(404, "正文不存在")
    if int(current.revision) != int(req.expected_revision):
        raise HTTPException(
            409,
            {
                "code": "DOCUMENT_CONFLICT",
                "message": "正文已在其他窗口更新，请刷新后重试。",
                "current": current.model_dump(),
            },
        )
    payload = build_candidate_set(
        session.root_dir,
        safe_id,
        source_text=current.plain_text,
        source_revision=int(current.revision),
        content_lock=req.content_lock,
        candidates=req.candidates,
        enabled=req.enabled,
        cost_budget=req.cost_budget,
        ttl_days=req.ttl_days,
    )
    touch_project_activity(session)
    return payload


@router.get("/api/manuscript/documents/{chapter_id}/candidate-set")
def get_candidate_set(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Return candidates together with feedback and deterministic ranking."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    payload = load_candidate_set(session.root_dir, safe_id)
    if not payload:
        raise HTTPException(404, "暂无候选集")
    return {
        **payload,
        "feedback": list_candidate_feedback(
            session.root_dir,
            safe_id,
            candidate_set_id=str(payload.get("candidate_set_id") or ""),
        ),
        "ranked_candidates": rank_candidates(session.root_dir, safe_id),
    }


@router.get("/api/manuscript/documents/{chapter_id}/candidate-set/timeline")
def get_candidate_set_timeline(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Return immutable candidate snapshots and the current best candidate."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    payload = load_candidate_set(session.root_dir, safe_id)
    if not payload:
        raise HTTPException(404, "暂无候选集")
    ranked = rank_candidates(session.root_dir, safe_id)
    return {
        "chapter_id": safe_id,
        "candidate_set_id": payload.get("candidate_set_id"),
        "timeline": list_candidate_timeline(session.root_dir, safe_id),
        "best_candidate": ranked[0] if ranked else None,
    }


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set/pairwise")
def post_candidate_pairwise_session(
    chapter_id: str,
    req: CandidatePairwiseRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Create a blind A/B review session without exposing candidate IDs."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    try:
        return create_pairwise_session(
            session.root_dir,
            safe_id,
            candidate_set_id=req.expected_candidate_set_id,
            candidate_a=req.candidate_a,
            candidate_b=req.candidate_b,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, "暂无候选集") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set/pairwise/{session_id}/feedback")
def post_candidate_pairwise_feedback(
    chapter_id: str,
    session_id: str,
    req: CandidatePairwiseFeedbackRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Resolve a blind choice server-side and record it as pairwise feedback."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    if not session_id or len(session_id) > 200 or "/" in session_id or "\\" in session_id:
        raise HTTPException(422, "session_id 无效")
    try:
        result = submit_pairwise_session(
            session.root_dir,
            safe_id,
            session_id,
            choice=req.choice,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, "盲选会话不存在") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return result


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set/candidates/{candidate_id}/adopt")
def adopt_candidate_set_candidate(
    chapter_id: str,
    candidate_id: str,
    req: CandidateAdoptRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Explicitly adopt one L0-passing candidate as a new manuscript revision."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    if not candidate_id or len(candidate_id) > 200 or "/" in candidate_id or "\\" in candidate_id:
        raise HTTPException(422, "candidate_id 无效")
    payload = load_candidate_set(session.root_dir, safe_id)
    if not payload:
        raise HTTPException(404, "暂无候选集")
    if str(payload.get("candidate_set_id") or "") != req.expected_candidate_set_id:
        raise HTTPException(
            409,
            {
                "code": "CANDIDATE_SET_CONFLICT",
                "message": "候选集已更新，请刷新后重试。",
                "candidate_set_id": payload.get("candidate_set_id"),
            },
        )
    if payload.get("status") == "expired":
        raise HTTPException(409, {"code": "CANDIDATE_SET_EXPIRED", "message": "候选集已过期"})
    current = build_manuscript_workspace(session.root_dir, chapter_id=safe_id).document
    if current is None:
        raise HTTPException(404, "正文不存在")
    if int(current.revision) != int(req.expected_revision):
        raise HTTPException(
            409,
            {
                "code": "DOCUMENT_CONFLICT",
                "message": "正文已在其他窗口更新，请刷新后重试。",
                "current": current.model_dump(),
            },
        )
    if str(payload.get("source_sha256") or "") != text_sha256(current.plain_text):
        raise HTTPException(
            409,
            {
                "code": "CANDIDATE_SET_STALE",
                "message": "候选集基于旧正文生成，请重新建立候选集。",
                "current_revision": int(current.revision),
            },
        )
    candidate = next(
        (
            item
            for item in payload.get("candidates", [])
            if isinstance(item, dict) and str(item.get("candidate_id")) == candidate_id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(404, "候选不存在")
    if str(candidate.get("status") or "") in {"rejected", "expired"}:
        raise HTTPException(409, {"code": "CANDIDATE_REJECTED", "message": "候选已被拒绝或过期"})
    validation = candidate.get("l0_validation") or {}
    if validation and validation.get("pass") is False:
        raise HTTPException(409, {"code": "CANDIDATE_L0_REJECTED", "message": "候选未通过本地 L0 校验"})
    candidate_text = str(candidate.get("text") or "")
    if not candidate_text.strip():
        raise HTTPException(409, {"code": "CANDIDATE_EMPTY", "message": "候选正文为空"})
    if text_sha256(candidate_text) == text_sha256(current.plain_text):
        event = record_candidate_feedback(
            session.root_dir,
            safe_id,
            {"kind": "accept", "candidate_id": candidate_id},
        )
        return {
            "status": "already_applied",
            "document": current.model_dump(),
            "event": event,
            "candidate_set": load_candidate_set(session.root_dir, safe_id),
            "ranked_candidates": rank_candidates(session.root_dir, safe_id),
        }
    try:
        document = apply_plain_text_to_manuscript(
            session.root_dir,
            chapter_id=safe_id,
            plain_text=candidate_text,
            title=current.title,
            expected_revision=int(req.expected_revision),
            source="manual",
        )
    except DocumentConflictError as exc:
        raise _conflict_response(exc) from exc
    event = record_candidate_feedback(
        session.root_dir,
        safe_id,
        {"kind": "accept", "candidate_id": candidate_id},
    )
    touch_project_activity(session)
    return {
        "status": "accepted",
        "document": document,
        "event": event,
        "candidate_set": load_candidate_set(session.root_dir, safe_id),
        "ranked_candidates": rank_candidates(session.root_dir, safe_id),
    }


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set/rollback")
def rollback_candidate_set(
    chapter_id: str,
    req: CandidateSetRollbackRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Restore a prior candidate-set snapshot without touching manuscript text."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    current = load_candidate_set(session.root_dir, safe_id)
    if not current:
        raise HTTPException(404, "暂无候选集")
    if str(current.get("candidate_set_id") or "") != req.expected_candidate_set_id:
        raise HTTPException(
            409,
            {
                "code": "CANDIDATE_SET_CONFLICT",
                "message": "候选集已更新，请刷新时间线后重试。",
                "candidate_set_id": current.get("candidate_set_id"),
            },
        )
    try:
        restored = restore_candidate_set_snapshot(session.root_dir, safe_id, req.timeline_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return {
        "status": "restored",
        "candidate_set": restored,
        "ranked_candidates": rank_candidates(session.root_dir, safe_id),
    }


@router.post("/api/manuscript/documents/{chapter_id}/candidate-set/feedback")
def post_candidate_feedback(
    chapter_id: str,
    req: CandidateFeedbackRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Record an explicit human feedback event without mutating manuscript text."""

    session = coerce_project_session(session)
    safe_id = _validate_id(chapter_id, "chapter_id")
    try:
        event = record_candidate_feedback(session.root_dir, safe_id, req.feedback)
    except FileNotFoundError as exc:
        raise HTTPException(404, "暂无候选集") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    touch_project_activity(session)
    return {
        "status": "recorded",
        "event": event,
        "candidate_set": load_candidate_set(session.root_dir, safe_id),
        "ranked_candidates": rank_candidates(session.root_dir, safe_id),
    }


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
