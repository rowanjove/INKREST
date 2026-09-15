"""Routes for Story Blueprint Compiler and Inspiration Workshop."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from novel_agent.domain.blueprint.blueprint import StoryBlueprint
from novel_agent.services.blueprint.blueprint_service import BlueprintService
from novel_agent.services.blueprint.validator import ValidationReport
from novel_agent.services.blueprint.incubator import IncubateResult
from novel_agent.services.blueprint.mutator import MutationResult
from novel_agent.services.blueprint.uniqueness import UniquenessAnalysisReport
from web.deps import ProjectSession, ProjectSessionDep, coerce_project_session

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])

_service: Optional[BlueprintService] = None


def get_service() -> BlueprintService:
    global _service
    if _service is None:
        _service = BlueprintService()
    return _service


class ValidateRequest(BaseModel):
    selected_atoms: list[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    selected_atoms: list[str] = Field(default_factory=list)
    limit: int = 6


class ComplianceCheckRequest(BaseModel):
    blueprint: dict[str, Any]
    draft_summary: str
    current_chapter_index: int = 1
    last_payoff_chapter: int = 1


class CompileRequest(BaseModel):
    selected_atoms: list[str] = Field(default_factory=list)
    recipe_id: Optional[str] = None
    user_inputs: dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[str] = None


class ApplyRequest(BaseModel):
    blueprint: dict[str, Any]
    project_id: Optional[str] = None


class IncubateRequest(BaseModel):
    idea: str = ""


class MutateRequest(BaseModel):
    current_atoms: list[str] = Field(default_factory=list)
    locked_dimensions: list[str] = Field(default_factory=list)


class UniquenessRequest(BaseModel):
    selected_atoms: list[str] = Field(default_factory=list)


@router.get("/components")
def get_components() -> dict[str, Any]:
    """Returns available atoms grouped by category/type."""
    service = get_service()
    return service.get_components()


@router.get("/recipes")
def get_recipes() -> list[dict[str, Any]]:
    """Returns all pre-defined trope recipes."""
    service = get_service()
    return service.get_recipes()


@router.post("/recommend")
def recommend_tropes(req: RecommendRequest) -> list[dict[str, Any]]:
    """Recommends complementary tropes based on current selections."""
    service = get_service()
    items = service.recommend_atoms(req.selected_atoms, limit=req.limit)
    return [i.model_dump() for i in items]


@router.post("/check-compliance")
def check_compliance(req: ComplianceCheckRequest) -> dict[str, Any]:
    """Audits draft outline or chapter text against Story Blueprint constraints."""
    service = get_service()
    bp = StoryBlueprint.model_validate(req.blueprint)
    report = service.check_compliance(
        blueprint=bp,
        draft_summary=req.draft_summary,
        current_chapter_index=req.current_chapter_index,
        last_payoff_chapter=req.last_payoff_chapter,
    )
    return report.model_dump()


@router.post("/incubate", response_model=IncubateResult)
def incubate_idea(req: IncubateRequest) -> IncubateResult:
    """Snowflake-style progressive inspiration derivation from a brainstorm idea."""
    service = get_service()
    return service.incubate_idea(req.idea)


@router.post("/mutate", response_model=MutationResult)
def mutate_blueprint(req: MutateRequest) -> MutationResult:
    """Produces conservative, moderate, and radical trope mutations."""
    service = get_service()
    return service.mutate_atoms(
        current_atom_ids=req.current_atoms,
        locked_dimensions=req.locked_dimensions,
    )


@router.post("/analyze-uniqueness", response_model=UniquenessAnalysisReport)
def analyze_uniqueness(req: UniquenessRequest) -> UniquenessAnalysisReport:
    """Evaluates market uniqueness, crowdedness, and provides anti-cliché differentiation suggestions."""
    service = get_service()
    return service.analyze_uniqueness(req.selected_atoms)


@router.post("/validate", response_model=ValidationReport)
def validate_atoms(req: ValidateRequest) -> ValidationReport:
    """Validates trope selections and checks for soft/hard narrative conflicts."""
    service = get_service()
    return service.validate_atoms(req.selected_atoms)


@router.post("/compile", response_model=StoryBlueprint)
def compile_blueprint(
    req: CompileRequest,
    session: ProjectSession = ProjectSessionDep,
) -> StoryBlueprint:
    """Compiles selected atoms, recipes, and inputs into a single StoryBlueprint."""
    service = get_service()
    session = coerce_project_session(session)
    project_id = req.project_id or (session.project_id if session.has_project else "")

    return service.compile(
        selected_atom_ids=req.selected_atoms,
        recipe_id=req.recipe_id,
        user_inputs=req.user_inputs,
        project_id=project_id,
    )


@router.post("/apply-to-project")
def apply_to_project(
    req: ApplyRequest,
    session: ProjectSession = ProjectSessionDep,
) -> dict[str, Any]:
    """Saves the compiled blueprint and writing guide to the project."""
    service = get_service()
    session = coerce_project_session(session)
    project_id = req.project_id or (session.project_id if session.has_project else "")

    if not project_id:
        return {"success": False, "message": "未指定作品或当前未打开作品"}

    try:
        bp = StoryBlueprint.model_validate(req.blueprint)
        bp.project_id = project_id
        saved = service.save_blueprint_to_project(project_id, bp)
        if not saved:
            return {"success": False, "message": "保存失败：作品目录不存在或路径受限", "project_id": project_id}
        return {"success": True, "project_id": project_id}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/current")
def get_current_blueprint(
    session: ProjectSession = ProjectSessionDep,
) -> dict[str, Any]:
    """Retrieves current project blueprint if one exists."""
    service = get_service()
    session = coerce_project_session(session)
    if not session.has_project:
        return {"has_blueprint": False, "blueprint": None}

    bp = service.load_blueprint_from_project(session.project_id)
    if bp:
        return {"has_blueprint": True, "blueprint": bp.model_dump()}
    return {"has_blueprint": False, "blueprint": None}
