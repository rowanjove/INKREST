from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChannelSpec(BaseModel):
    id: str = "general"
    label: str = "通用"


class GenreSpec(BaseModel):
    primary: str = ""
    secondary: list[str] = Field(default_factory=list)


class ProtagonistSpec(BaseModel):
    name: str = "主角"
    archetype: str = ""
    identity: str = ""
    core_desire: str = ""
    flaw: str = ""


class WorldSpec(BaseModel):
    structure: str = ""
    scarcity: str = ""
    power_system: str = ""
    core_conflict: str = ""


class MechanismSpec(BaseModel):
    id: str
    name: str
    category: str = "gold_finger"
    parameters: dict[str, Any] = Field(default_factory=dict)


class EmotionSpec(BaseModel):
    id: str
    name: str
    frequency: str = "medium"


class NarrativeSpec(BaseModel):
    structure: str = "linear_progression"
    viewpoint: str = "third_person_limited"
    pacing: str = "fast"
    style_tone: str = "balanced"


class StoryDNA(BaseModel):
    """Ten-dimensional Story DNA."""

    channel: ChannelSpec = Field(default_factory=ChannelSpec)
    genres: GenreSpec = Field(default_factory=GenreSpec)
    protagonist: ProtagonistSpec = Field(default_factory=ProtagonistSpec)
    world: WorldSpec = Field(default_factory=WorldSpec)
    mechanisms: list[MechanismSpec] = Field(default_factory=list)
    core_conflict: str = ""
    emotional_engines: list[EmotionSpec] = Field(default_factory=list)
    narrative: NarrativeSpec = Field(default_factory=NarrativeSpec)


class USP(BaseModel):
    """Unique Selling Proposition / Core selling point."""

    one_sentence_hook: str = ""
    core_fantasy: list[str] = Field(default_factory=list)
    novelty_points: list[str] = Field(default_factory=list)
    reader_promise_summary: str = ""


class ReaderPromise(BaseModel):
    """Explicit expectation contract with readers and intervals."""

    id: str
    promise_type: str  # progression | mystery | emotional_payoff | relationship
    description: str
    expected_interval: str = "3-5"  # chapters
    payoff_stage: str = ""


class PacingVolume(BaseModel):
    volume_index: int = 1
    title: str = "第一卷"
    opening_hook: int = 8  # 1-10 intensity
    climax_target: int = 9
    cool_points: list[str] = Field(default_factory=list)


class PacingPlan(BaseModel):
    volumes: list[PacingVolume] = Field(default_factory=list)
    target_chapters: int = 100
    rhythm_pattern: str = "fast_paced_web_novel"


class WorldConstraintRule(BaseModel):
    name: str
    rule_type: str = "power_law"
    condition: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)


class CharacterArc(BaseModel):
    character_name: str
    start_belief: str = ""
    want: str = ""
    need: str = ""
    midpoint_crisis: str = ""
    end_belief: str = ""


class StoryBlueprint(BaseModel):
    """The master narrative contract compiled from tropes, user intent, and rules."""

    schema_version: int = 1
    id: str
    project_id: str = ""
    title: str = ""
    revision: int = 1
    created_at: str = ""
    updated_at: str = ""

    dna: StoryDNA = Field(default_factory=StoryDNA)
    selected_atoms: list[str] = Field(default_factory=list)
    selected_recipe_id: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)

    usp: USP = Field(default_factory=USP)
    reader_promises: list[ReaderPromise] = Field(default_factory=list)
    pacing: PacingPlan = Field(default_factory=PacingPlan)
    world_constraints: list[WorldConstraintRule] = Field(default_factory=list)
    character_arcs: list[CharacterArc] = Field(default_factory=list)

    # Derived outputs
    writing_guide_markdown: str = ""
    outline_contract: dict[str, Any] = Field(default_factory=dict)
    review_rules: list[dict[str, Any]] = Field(default_factory=list)
