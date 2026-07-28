"""V2 planning workspace routes."""

from fastapi import APIRouter

from novel_agent.domain.planning import PlanningWorkspace
from novel_agent.services.planning_workspace import build_planning_workspace
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

router = APIRouter()


@router.get("/api/planning/workspace", response_model=PlanningWorkspace)
def get_planning_workspace(
    session: ProjectSession = RequireProjectDep,
) -> PlanningWorkspace:
    session = coerce_project_session(session)
    return build_planning_workspace(session.root_dir)
