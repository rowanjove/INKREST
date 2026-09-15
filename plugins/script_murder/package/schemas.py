"""Data models and schemas for Inkrest Script Murder Workshop."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Project Metadata
# ---------------------------------------------------------------------------

class ProjectMeta(BaseModel):
    """Basic project identity and production settings."""
    id: str = Field(..., description="Unique project ID")
    title: str = Field("未命名剧本", min_length=1, max_length=120)
    player_count: int = Field(6, ge=1, le=16, description="Number of players")
    duration_minutes: int = Field(240, ge=60, le=720, description="Estimated play time in minutes")
    genre: List[str] = Field(
        default_factory=lambda: ["本格推理"],
        description="Genres: 本格推理, 变格推理, 情感, 机制, 阵营, 还原, 刑侦, 惊悚等",
    )
    tone: List[str] = Field(
        default_factory=lambda: ["冷峻", "写实"],
        description="Atmosphere/Tone",
    )
    era: str = Field("1998年", description="Historical period or era")
    setting: str = Field("北方沿海港口城市", description="Geographic/environmental setting")
    difficulty: int = Field(4, ge=1, le=5, description="Difficulty level from 1 (entry) to 5 (hardcore)")
    style: str = Field("hardcore", description="hardcore / narrative / social / puzzle")
    status: Literal["planning", "canon_ready", "writing", "auditing", "ready"] = "planning"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


# ---------------------------------------------------------------------------
# 2. Truth Canon (The Absolute Objective World State)
# ---------------------------------------------------------------------------

class TruthFact(BaseModel):
    """An atomic, unalterable historical fact in the objective world."""
    id: str = Field(..., description="Stable Fact ID, e.g. 'F001'")
    category: Literal["crime", "motive", "timeline", "trace", "background"] = "crime"
    title: str = Field(..., min_length=2, max_length=64)
    content: str = Field(..., min_length=4, max_length=2000, description="Objective truth without narrative spin")
    occurred_at: Optional[str] = Field(None, description="Timestamp, e.g. '21:15' or '1998-03-20 21:15'")
    location: str = Field("", description="Specific location of occurrence")
    actors: List[str] = Field(default_factory=list, description="IDs of characters involved in this fact")
    is_core_truth: bool = Field(True, description="Whether this fact is essential for solving the mystery")
    revealed_round: int = Field(0, description="Round where this fact is fully revealed (0 = unrevealed until review)")


class TruthCanon(BaseModel):
    """The canonical, ground-truth reality designed for the game."""
    victim: str = Field("", description="Victim name or identifier")
    killer: str = Field("", description="True killer character ID")
    cause_of_death: str = Field("", description="Medical/Physical cause of death")
    crime_time_window: Tuple[str, str] = Field(
        default=("21:00", "21:30"),
        description="Exact window when lethal event occurred",
    )
    crime_scene: str = Field("", description="Exact location where murder occurred")
    crime_method: str = Field("", description="Physical murder method & mechanics")
    true_motive: str = Field("", description="Underlying genuine motive")
    facts: List[TruthFact] = Field(default_factory=list)
    revision: int = Field(1, ge=1)


# ---------------------------------------------------------------------------
# 3. Characters & Epistemic Boundaries (Truth / Knowledge / Belief / Lie)
# ---------------------------------------------------------------------------

class CharacterKnowledgeItem(BaseModel):
    """A character's subjective epistemic state regarding a specific Fact."""
    fact_id: str = Field(..., description="Refers to TruthFact.id")
    epistemic_state: Literal["knowledge", "belief", "lie"] = Field(
        ...,
        description=(
            "knowledge: Character experienced or reliably witnessed the fact. "
            "belief: Character holds subjective conviction which may be mistaken. "
            "lie: Character intentionally fabricates an untruth or conceals truth."
        ),
    )
    narrative_statement: str = Field(
        ...,
        description="What the character actually perceives or claims to believe/say",
    )
    allowed_to_reveal: bool = Field(
        True,
        description="Whether character is allowed to volunteer this information proactively",
    )
    revealed_in_round: int = Field(1, ge=1, description="Round when character acquires this memory/knowledge")


class CharacterTimelineEvent(BaseModel):
    """A point on a character's chronological trajectory."""
    time: str = Field(..., description="Clock time, e.g. '20:30'")
    location: str = Field(..., description="Physical location")
    activity_real: str = Field(..., description="What the character actually did at this moment")
    activity_claimed: str = Field(..., description="What the character claims in their alibi")
    is_alibi_claim: bool = Field(False)
    has_witness: bool = Field(False)
    witness_ids: List[str] = Field(default_factory=list)


class CharacterProfile(BaseModel):
    """A player character sheet with strict visibility boundaries."""
    id: str = Field(..., description="Unique character ID, e.g. 'CHAR_01'")
    name: str = Field(..., min_length=1, max_length=32)
    gender: str = Field("未知")
    age: int = Field(28, ge=1, le=120)
    public_identity: str = Field(..., description="Identity known to all players at opening")
    private_background: str = Field("", description="Deep personal history revealed only to this player")
    desire: str = Field("", description="Primary driving desire")
    secrets: List[str] = Field(default_factory=list, description="Private secrets player must conceal")
    personal_goals: List[str] = Field(default_factory=list, description="In-game objectives for this player")
    relationships: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of character_id -> subjective relationship description",
    )
    timeline: List[CharacterTimelineEvent] = Field(default_factory=list)
    knowledge_map: List[CharacterKnowledgeItem] = Field(default_factory=list)
    script_acts: Dict[str, str] = Field(
        default_factory=dict,
        description="Act-by-act written script for this character: {'act_1': '...', 'act_2': '...'}",
    )


# ---------------------------------------------------------------------------
# 4. Clue Graph & Deductive Chains (Fact -> Clue -> Inference -> Conclusion)
# ---------------------------------------------------------------------------

class ClueItem(BaseModel):
    """A physical object, testimony, trace, or document discoverable by players."""
    id: str = Field(..., description="Clue ID, e.g. 'C001'")
    title: str = Field(..., min_length=2, max_length=64)
    clue_type: Literal["physical", "forensic", "trace", "document", "testimony"] = "physical"
    round: int = Field(1, ge=1, description="Round in which this clue becomes discoverable")
    location: str = Field("", description="Where the clue is found (e.g. '仓库西侧货架')")
    owner: Optional[str] = Field(None, description="Character ID who holds this clue if private")
    visibility: Literal["public", "private", "lockable"] = "public"
    content: str = Field(
        ...,
        min_length=4,
        description="Cold, forensic, objective description of the physical clue without narrative spoiler",
    )
    fact_refs: List[str] = Field(
        default_factory=list,
        description="List of TruthFact.id that this clue materially evidences",
    )
    supports_conclusions: List[str] = Field(
        default_factory=list,
        description="List of Conclusion.id that this clue helps prove",
    )
    is_red_herring: bool = Field(
        False,
        description="Whether this clue is intentionally designed as a misleading decoy",
    )
    debunk_clue_refs: List[str] = Field(
        default_factory=list,
        description="Clue IDs required to dismiss this red herring",
    )
    required: bool = Field(
        True,
        description="Whether this clue is strictly required to reach the true conclusion",
    )


class DeductiveConclusion(BaseModel):
    """A pivotal deductive milestone required to crack the case."""
    id: str = Field(..., description="Conclusion ID, e.g. 'CONCL_01'")
    title: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., description="Logical deduction statement")
    supported_by_clues: List[str] = Field(
        default_factory=list,
        description="List of ClueItem.id that together prove this conclusion",
    )
    proves_fact_id: Optional[str] = Field(None, description="Associated Fact ID being corroborated")
    target_suspect_id: Optional[str] = Field(None, description="Suspect implicated or exonerated")
    is_mandatory: bool = Field(True, description="Whether game cannot be solved without this conclusion")


# ---------------------------------------------------------------------------
# 5. Game Flow & Rounds
# ---------------------------------------------------------------------------

class GameRound(BaseModel):
    """A gameplay phase/round with structured information release."""
    round_index: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=64)
    stage_objective: str = Field("", description="What players should focus on in this round")
    search_clue_ids: List[str] = Field(default_factory=list, description="Clues discoverable in this round")
    public_events: List[str] = Field(default_factory=list, description="Host-announced events or new discoveries")
    vote_required: bool = Field(False)
    discussion_minutes: int = Field(45, ge=10, le=180)


class GameFlow(BaseModel):
    """Complete progression structure of the mystery."""
    prologue: str = Field("", description="Host opening narrative")
    rounds: List[GameRound] = Field(default_factory=list)
    epilogue_killer: str = Field("", description="Ending narrative if killer is caught")
    epilogue_escape: str = Field("", description="Ending narrative if killer escapes")


# ---------------------------------------------------------------------------
# 6. Complete Project Aggregate State
# ---------------------------------------------------------------------------

class ScriptMurderWorkspace(BaseModel):
    """In-memory aggregate of a complete murder mystery project."""
    meta: ProjectMeta
    # Structured project data is authoritative; generated text remains a projection.
    brief: Dict[str, Any] = Field(default_factory=dict)
    canon: TruthCanon = Field(default_factory=TruthCanon)
    characters: List[CharacterProfile] = Field(default_factory=list)
    clues: List[ClueItem] = Field(default_factory=list)
    conclusions: List[DeductiveConclusion] = Field(default_factory=list)
    flow: GameFlow = Field(default_factory=GameFlow)
    host_guide: str = Field("", description="Full Host Manual markdown")
    documents: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated/public documents keyed by stable document ID",
    )
    revision: int = Field(1, ge=1)
    revisions: Dict[str, int] = Field(
        default_factory=lambda: {
            "brief": 1,
            "canon": 1,
            "characters": 1,
            "clues": 1,
            "flow": 1,
            "documents": 1,
        }
    )
    artifact_status: Dict[str, Literal["current", "stale", "missing"]] = Field(
        default_factory=lambda: {
            "characters": "missing",
            "clues": "missing",
            "flow": "missing",
            "scripts": "missing",
            "host_guide": "missing",
            "audit": "missing",
            "playtest": "missing",
            "export": "missing",
        }
    )
    dependency_hashes: Dict[str, str] = Field(default_factory=dict)


class GenerationTaskRecord(BaseModel):
    """Persisted, user-observable AI or validation task."""

    id: str
    project_id: str
    node: str
    status: Literal[
        "queued", "running", "succeeded", "failed", "cancelled", "superseded"
    ] = "queued"
    apply_state: Literal["pending", "applied", "rejected"] = "applied"
    input_revision: int = 1
    dependency_hash: str = ""
    model: str = "offline"
    prompt_version: str = "1"
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cancel_requested: bool = False


# ---------------------------------------------------------------------------
# 7. Deterministic Validation Report
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    severity: Literal["BLOCKER", "ERROR", "WARNING", "INFO"]
    code: str
    message: str
    target_id: Optional[str] = None
    fix_suggestion: Optional[str] = None


class ValidationReport(BaseModel):
    is_valid: bool = True
    blocker_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    issues: List[ValidationIssue] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(
        default_factory=lambda: {
            "evidence_chain_closure_rate": 1.0,
            "orphan_clues_count": 0,
            "temporal_conflicts_count": 0,
            "visibility_leak_count": 0,
        }
    )
