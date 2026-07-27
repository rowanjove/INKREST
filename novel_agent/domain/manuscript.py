"""Stable contracts for the V2 manuscript center."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ManuscriptDocument(BaseModel):
    document_id: str
    chapter_id: str
    title: str
    content_json: Dict[str, Any]
    plain_text: str
    markdown_text: str
    revision: int
    source: str = "import"
    created_at: str
    updated_at: str


class ManuscriptRevision(BaseModel):
    revision_id: str
    document_id: str
    chapter_id: str
    revision: int
    title: str
    content_json: Dict[str, Any]
    plain_text: str
    markdown_text: str
    source: str
    created_at: str


class ManuscriptChapter(BaseModel):
    chapter_id: str
    title: str
    word_count: int = 0
    status: str = "draft"
    status_label: str = "草稿"
    has_content: bool = False


class ManuscriptWorkspace(BaseModel):
    schema_version: int = 1
    chapters: List[ManuscriptChapter] = Field(default_factory=list)
    selected_chapter_id: str = ""
    document: Optional[ManuscriptDocument] = None
    history: List[ManuscriptRevision] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
