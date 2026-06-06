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


@router.post("/api/novel/chat")
def novel_chat(req: NovelChatRequest) -> Dict[str, Any]:
    """AI-guided creation: one step of the 6-step base or 4-step deep flow."""
    from novel_agent.pipeline import PipelineConfig
    from web.novel_chat import NovelChatHandler

    root = ws_server.get_root_dir()
    config = PipelineConfig.from_config(root)
    handler = NovelChatHandler(config.get_llm("novel_chat"))
    return handler.handle_step(req.step, req.user_input, req.context)


@router.get("/api/novel/chat/intro/{step}")
def novel_chat_intro(step: int) -> Dict[str, Any]:
    """Get the intro message for a chat step (before user input)."""
    from web.novel_chat import NovelChatHandler

    # Intro doesn't need LLM, just return static messages
    handler = NovelChatHandler(llm=None)  # type: ignore
    return handler.get_intro(step)

