from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# ---- Request models ----

class ChapterRequest(BaseModel):
    chapter_id: str = Field(default="001", pattern=r'^[a-zA-Z0-9_-]+$')
    goal: str = Field(..., min_length=1)
    dry_run: bool = False


class BatchChapterRequest(BaseModel):
    chapters: List[ChapterRequest]
    dry_run: bool = False


class AssetUpdate(BaseModel):
    content: str


class AssetCreate(BaseModel):
    name: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    label: str = ""
    extension: str = Field(default="md", pattern=r'^(md|yaml|yml|json|txt)$')
    content: str = ""


class AssetGenerateRequest(BaseModel):
    name: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    label: str = ""
    asset_type: str = "角色卡"
    count: int = Field(default=3, ge=1, le=50)
    attributes: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    instructions: str = ""


class ConfigUpdate(BaseModel):
    llm: Optional[Dict[str, Any]] = None
    embedding: Optional[Dict[str, Any]] = None
    runtime: Optional[Dict[str, Any]] = None
    chapter: Optional[Dict[str, Any]] = None


class NovelPlanRequest(BaseModel):
    """Request to generate a novel outline."""
    theme: str = Field(..., min_length=1)
    genre: str = Field(default="玄幻")
    target_chapters: int = Field(default=20, ge=1, le=3000)
    scale: str = ""
    scale_label: str = ""
    special_requirements: str = ""
    overwrite: bool = False


class ChapterPlanRequest(BaseModel):
    """Request to generate a chapter queue from the current outline."""
    start_chapter: int = Field(default=1, ge=1, le=9999)
    count: int = Field(default=10, ge=1, le=200)
    instructions: str = ""


class NovelRunRequest(BaseModel):
    """Request to run the full novel generation pipeline."""
    theme: str = Field(..., min_length=1)
    genre: str = Field(default="玄幻")
    target_chapters: int = Field(default=20, ge=1, le=3000)
    scale: str = ""
    scale_label: str = ""
    special_requirements: str = ""
    dry_run: bool = False


class NovelArcRunRequest(BaseModel):
    """Run one or more arcs from workspace/arc_*.json."""
    arc_id: str = ""
    arc_ids: List[str] = Field(default_factory=list)
    start_arc_id: str = ""
    resume: bool = True
    max_chapters: int = Field(
        default=0,
        ge=0,
        le=500,
        description="0=本卷队列跑完；>0=本轮最多生成章数",
    )
    dry_run: bool = False


class NovelContinueRequest(BaseModel):
    """Resume arc batch from novel_batch_progress.json."""
    resume: bool = True
    max_chapters: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="0=按档位/大纲剩余自动跑满；>0=本轮或自动续跑总章数上限",
    )
    dry_run: bool = False
    autopilot: bool = Field(
        default=False,
        description="后台多轮续跑：每轮排空队列并补窗，直至上限/熔断/无待写章",
    )
    full_book: bool = Field(
        default=True,
        description="autopilot 时 True=全书弧排空；False=从 last_arc_id 续跑",
    )
    chapters_per_round: int = Field(
        default=0,
        ge=0,
        le=100,
        description="autopilot 每轮最多生成章数，0=用 pipeline runtime 默认",
    )
    max_rounds: int = Field(default=0, ge=0, le=2000)
    force_resume: bool = Field(
        default=False,
        description="True=熔断暂停后仍续跑；默认需先处理阻断章",
    )


class NovelChatRequest(BaseModel):
    """Request for one step of AI-guided novel creation."""
    step: int = Field(..., ge=1, le=10)
    user_input: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


# ---- Response models ----

class ChapterSummary(BaseModel):
    chapter_id: str
    title: str
    word_count: int
    risk_level: str
    final_path: str
    is_missing: bool = False
    has_final: bool = True
    gate_status: str = ""


class ChapterListResponse(BaseModel):
    items: List[ChapterSummary]
    total: int
    offset: int
    limit: int
    indexed: bool = True


class ChapterDetail(BaseModel):
    chapter_id: str
    title: str
    final_text: str
    plan: Dict[str, Any]
    wordcount: Dict[str, Any]
    audit: Dict[str, Any]
    continuity: Dict[str, Any]
    state_update: Dict[str, Any]
    chapter_summary: str
    quality_report: Dict[str, Any] = Field(default_factory=dict)
    unified_gate: Dict[str, Any] = Field(default_factory=dict)
    checkpoint: Dict[str, Any] = Field(default_factory=dict)
    artifact_status: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_summary: Dict[str, Any] = Field(default_factory=dict)
    external_review_status: str = "none"


class ExternalReviewUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(none|pending_external|external_passed)$")
    note: str = ""


class TrialExportRequest(BaseModel):
    chapter_ids: List[str] = Field(default_factory=list)
    include_titles: bool = True


class TaskStatus(BaseModel):
    task_id: str
    project_id: Optional[str] = None
    task_type: Optional[str] = None
    status: Literal[
        "pending",
        "claimed",
        "running",
        "paused",
        "succeeded",
        "failed",
        "cancelled",
    ]
    chapter_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    resumable_from: Optional[str] = None
    status_reason: Optional[str] = None


class StateView(BaseModel):
    characters: Dict[str, Any]
    foreshadows: List[Dict[str, Any]]
    hooks: List[Dict[str, Any]]
    objects: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    threads: List[Dict[str, Any]]


class TimelineView(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    foreshadows: List[Dict[str, Any]]
    hooks: List[Dict[str, Any]]


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    preset_id: Optional[str] = None
    genre: str = ""
    channel: str = ""
    target_chapters: int = 0
    scale: str = ""
    scale_label: str = ""
    scale_profile: Dict[str, Any] = {}
    target_chars_per_chapter: List[int] = []
    outline: Optional[Dict[str, Any]] = None
    preset_channel: Optional[str] = None
    preset_theme: Optional[str] = None
    preset_mechanisms: List[str] = []
    preset_cool_points: List[str] = []
    platform: Optional[str] = "qidian"


class ComposeRequest(BaseModel):
    channel: str = "general"
    theme: str
    mechanisms: List[str] = []
    cool_points: List[str] = []
    project_id: Optional[str] = None


class ModelSaveRequest(BaseModel):
    id: str
    name: str = ""
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 120
    proxy: str = ""
    type: str = "text"  # 'text' or 'image'


class ModelSlotRequest(BaseModel):
    """文字模型档位：daily / reasoning 各唯一，backup 可多个，空=不参与。"""

    slot: str = Field(
        default="",
        description="空字符串 | daily | reasoning | backup",
    )


class ModelTestRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: Optional[str] = None
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 30
    proxy: str = ""
    type: str = "text"


class SaveChapterRequest(BaseModel):
    title: Optional[str] = None
    final_text: str


class AnalyzeIntroRequest(BaseModel):
    text: str


class GenerateCoverRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    prompt: str


class SaveCoverRequest(BaseModel):
    cover: str  # Base64 data url or raw base64 string


class RewriteDescriptionRequest(BaseModel):
    old_description: str
    style: str = "爽文吸睛"
    user_preference: str = ""


class UpdateDescriptionRequest(BaseModel):
    description: str


class UpdatePlatformRequest(BaseModel):
    platform: str


class UpdateAuthorLabelRequest(BaseModel):
    author_label: str = ""
