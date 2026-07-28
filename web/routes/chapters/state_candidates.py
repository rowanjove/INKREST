"""Chapter state change candidate review."""

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session, task_manager_for

ws_server._validate_id = ws_helpers._validate_id

router = APIRouter()


class CandidateActionRequest(BaseModel):
    action: str = Field(..., pattern=r"^(accept|reject)$")


@router.get("/api/chapters/{chapter_id}/state-candidates")
def get_state_candidates(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    ws_server._validate_id(chapter_id, "chapter_id")
    store = task_manager_for(session).store
    return store.list_state_change_candidates(chapter_id=chapter_id)


@router.post("/api/chapters/{chapter_id}/state-candidates/approve")
def approve_all_candidates(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    ws_server._validate_id(chapter_id, "chapter_id")
    store = task_manager_for(session).store
    store.accept_chapter_candidates(chapter_id)
    return {"status": "success", "message": f"Approved all state candidates for chapter {chapter_id}"}


@router.post("/api/chapters/state-candidates/{candidate_id}/action")
def action_on_candidate(
    candidate_id: str,
    req: CandidateActionRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    store = task_manager_for(session).store
    if req.action == "accept":
        store.accept_candidate(candidate_id)
        return {"status": "success", "message": f"Candidate {candidate_id} accepted and synced"}
    store.update_candidate_status(candidate_id, "rejected")
    return {"status": "success", "message": f"Candidate {candidate_id} rejected"}
