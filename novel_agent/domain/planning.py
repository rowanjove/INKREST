"""Stable read contract for the V2 planning workspace."""

from typing import Any

from pydantic import BaseModel, Field


class PlanningEntity(BaseModel):
    id: str
    kind: str
    name: str
    summary: str = ""
    source: str
    configured: dict[str, Any] = Field(default_factory=dict)
    current_state: dict[str, Any] = Field(default_factory=dict)
    related_chapters: list[str] = Field(default_factory=list)


class PlanningRelation(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""
    intensity: float = 0.0
    chapter_id: str = ""
    description: str = ""


class PlanningWorkspace(BaseModel):
    schema_version: int = 1
    entities: list[PlanningEntity] = Field(default_factory=list)
    relations: list[PlanningRelation] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
