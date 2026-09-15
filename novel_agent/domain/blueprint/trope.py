from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class TropeAtom(BaseModel):
    """Smallest narrative building block in the Story Blueprint system."""

    id: str
    name: str
    type: str  # channel | genre | world_structure | protagonist | desire | mechanism | conflict | emotional_engine | narrative | pacing | cool_point
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)  # male | female | general
    description: str = ""
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    requires: list[str] = Field(default_factory=list)
    recommended_with: list[str] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list)
    weak_conflicts: list[str] = Field(default_factory=list)
    emotional_functions: list[str] = Field(default_factory=list)
    pacing_impact: str = ""
    built_in: bool = True


class TropeRelation(BaseModel):
    """Explicit relationship edge between two trope atoms."""

    source_id: str
    target_id: str
    relation_type: str  # requires | recommended_with | conflicts_with | weak_conflict | enhances
    reason: str = ""
