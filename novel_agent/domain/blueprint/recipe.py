from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class TropeRecipe(BaseModel):
    """A proven combination of atoms, parameters, and pacing templates."""

    id: str
    name: str
    channel: str = "male"  # male | female | general
    category: str = ""
    subcategory: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    atoms: list[str] = Field(default_factory=list)
    default_parameters: dict[str, Any] = Field(default_factory=dict)
    pacing_template: dict[str, Any] = Field(default_factory=dict)
    writing_guide: str = ""
    built_in: bool = True
