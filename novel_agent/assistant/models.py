from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PatchStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED = "rejected"
    REVERTED = "reverted"


class SourceType(str, Enum):
    CHARACTER = "character"
    WORLD = "world"
    CHAPTER = "chapter"
    OUTLINE = "outline"
    TIMELINE = "timeline"
    FORESHADOWING = "foreshadowing"
    GATE_REPORT = "gate_report"


class EditorRange(BaseModel):
    from_pos: int = Field(0, description="Start index in document text")
    to_pos: int = Field(0, description="End index in document text")


class ActiveEditorContext(BaseModel):
    project_id: Optional[str] = None
    chapter_id: Optional[str] = None
    selected_text: Optional[str] = None
    selection_range: Optional[EditorRange] = None
    cursor_before_text: Optional[str] = None
    cursor_after_text: Optional[str] = None
    scene_id: Optional[str] = None
    active_characters: List[str] = Field(default_factory=list)


class CitationReference(BaseModel):
    source_type: SourceType
    source_id: str
    title: str
    snippet: str = ""
    anchor: Optional[str] = None
    chapter_id: Optional[str] = None
    url: Optional[str] = None


class AssistantPatch(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    project_id: str
    chapter_id: str
    thread_id: Optional[str] = None
    source_range: Optional[EditorRange] = None
    original_text: str
    proposed_text: str
    reason: str = ""
    skill_id: Optional[str] = None
    status: PatchStatus = PatchStatus.PROPOSED
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthorPreference(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    scope: str = "global"  # 'global' | 'project'
    project_id: Optional[str] = None
    preference_type: str = "style"  # 'style' | 'taboo' | 'habit'
    content: str
    created_at: Optional[str] = None


class AssistantMessageRecord(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    thread_id: str
    role: str
    content: str
    skill_id: Optional[str] = None
    model_id: Optional[str] = None
    citations: List[CitationReference] = Field(default_factory=list)
    patch_id: Optional[str] = None
    created_at: Optional[str] = None


class ToolCallStep(BaseModel):
    model_config = {"protected_namespaces": ()}

    step_index: int = 0
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Any = None
    permission_level: int = 0
    status: str = "success"  # 'success' | 'error' | 'requires_confirmation'
    elapsed_ms: int = 0
    error: Optional[str] = None


class RunRecord(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    thread_id: Optional[str] = None
    project_id: Optional[str] = None
    skill_id: Optional[str] = None
    model_id: Optional[str] = None
    status: str = "running"  # 'running' | 'completed' | 'requires_confirmation' | 'failed'
    steps: List[ToolCallStep] = Field(default_factory=list)
    output_text: str = ""
    total_elapsed_ms: int = 0
    created_at: Optional[str] = None

