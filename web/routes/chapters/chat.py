"""Novel creation chat flow."""

from typing import Any, Dict

from fastapi import APIRouter

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session
from web.models import NovelChatRequest

ws_server._validate_id = ws_helpers._validate_id
ws_server._read_json = ws_helpers._read_json
ws_server._read_text = ws_helpers._read_text
ws_server.get_outline = ws_helpers.get_outline
ws_server._delete_chapter_dir = ws_helpers._delete_chapter_dir

router = APIRouter()


@router.post("/api/novel/chat")
def novel_chat(req: NovelChatRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    """AI-guided creation: one step of the 6-step base or 4-step deep flow."""
    from novel_agent.pipeline import PipelineConfig
    from web.novel_chat import NovelChatHandler

    session = coerce_project_session(session)
    config = PipelineConfig.from_config(session.root_dir)
    handler = NovelChatHandler(config.get_llm("novel_chat"))
    return handler.handle_step(req.step, req.user_input, req.context)


@router.get("/api/novel/chat/intro/{step}")
def novel_chat_intro(step: int) -> Dict[str, Any]:
    """Get the intro message for a chat step (before user input)."""
    from web.novel_chat import NovelChatHandler

    handler = NovelChatHandler(llm=None)  # type: ignore
    return handler.get_intro(step)