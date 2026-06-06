"""Shared imports for chapter route modules."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import web.context as ws_server
import web.helpers as ws_helpers

ws_server._validate_id = ws_helpers._validate_id
ws_server._read_json = ws_helpers._read_json
ws_server._read_text = ws_helpers._read_text
ws_server.get_outline = ws_helpers.get_outline
ws_server._delete_chapter_dir = ws_helpers._delete_chapter_dir
ws_server.logger = logging.getLogger("web.server")

from web.models import (
    ChapterRequest,
    BatchChapterRequest,
    TaskStatus,
    ChapterSummary,
    ChapterDetail,
    NovelChatRequest,
    SaveChapterRequest,
)
from novel_agent.scripts.count_chars import count_chinese_chars, wordcount_report

router = APIRouter()


class CandidateActionRequest(BaseModel):
    action: str = Field(..., pattern=r'^(accept|reject)$')


@router.get("/api/chapters/{chapter_id}/state-candidates")
def get_state_candidates(chapter_id: str) -> List[Dict[str, Any]]:
    ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    return store.list_state_change_candidates(chapter_id=chapter_id)


@router.post("/api/chapters/{chapter_id}/state-candidates/approve")
def approve_all_candidates(chapter_id: str) -> Dict[str, Any]:
    ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    store.accept_chapter_candidates(chapter_id)
    return {"status": "success", "message": f"Approved all state candidates for chapter {chapter_id}"}


@router.post("/api/chapters/state-candidates/{candidate_id}/action")
def action_on_candidate(candidate_id: str, req: CandidateActionRequest) -> Dict[str, Any]:
    store = ws_server._get_task_manager().store
    if req.action == "accept":
        store.accept_candidate(candidate_id)
        return {"status": "success", "message": f"Candidate {candidate_id} accepted and synced"}
    else:
        store.update_candidate_status(candidate_id, "rejected")
        return {"status": "success", "message": f"Candidate {candidate_id} rejected"}

