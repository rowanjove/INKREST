"""Stable production-center read contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from novel_agent.domain.project_snapshot import ProjectSnapshot


class ProductionWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    snapshot: ProjectSnapshot
    tasks: list[dict[str, Any]]
    events: list[dict[str, Any]]
    task_logs: list[dict[str, Any]]
    runtime_logs: list[dict[str, Any]]
    reviews: dict[str, Any]
    section_errors: dict[str, str]
    updated_at: datetime
