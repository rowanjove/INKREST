"""Stable project snapshot contract for HTTP, integrations, and desktop state."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from novel_agent.domain.tasks import TaskRecord


class ProjectSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: dict[str, Any]
    workflow_mode: Literal["assisted", "factory"]
    readiness: dict[str, Any]
    outline_progress: dict[str, Any]
    chapter_progress: dict[str, Any]
    active_tasks: list[TaskRecord]
    blocking_issues: list[dict[str, Any]]
    quality_summary: dict[str, Any]
    cost_summary: dict[str, Any]
    next_actions: list[dict[str, Any]]
    updated_at: datetime
