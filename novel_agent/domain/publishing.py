"""Stable contracts for publication preview and export."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from novel_agent.domain.project_snapshot import ProjectSnapshot


class PublicationChapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str
    title: str
    plain_text: str
    markdown_text: str
    revision: int
    word_count: int = 0

    @property
    def text(self) -> str:
        """Compatibility alias for legacy first-party exporter adapters."""
        return self.plain_text


class PublicationBook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    author: str = "栖墨"
    language: str = "zh-CN"
    chapters: list[PublicationChapter] = Field(default_factory=list)


class PreflightItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["blocking", "warning", "ready"]
    label: str
    detail: str
    route: str = ""


class ExportPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_export: bool
    blocking_count: int
    warning_count: int
    items: list[PreflightItem] = Field(default_factory=list)


class PublishingWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    snapshot: ProjectSnapshot
    book: PublicationBook
    selected_chapter_id: str = ""
    selected_chapter: PublicationChapter | None = None
    platform: dict
    platform_check: dict
    golden_check: dict
    feedback: list[dict]
    preflight: ExportPreflight
    formats: list[dict]
