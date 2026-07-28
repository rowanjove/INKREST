"""Contract: project-scoped routes use ProjectSession dependency injection."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROJECT_SCOPED_ROUTE_FILES = (
    "web/routes/factory.py",
    "web/routes/chapters/tasks.py",
    "web/routes/chapters/crud.py",
    "web/routes/chapters/extras.py",
    "web/routes/chapters/snapshots.py",
    "web/routes/chapters/chat.py",
    "web/routes/chapters/versions.py",
    "web/routes/chapters/state_candidates.py",
    "web/routes/outlines.py",
    "web/routes/assistant.py",
    "web/routes/agent_api.py",
    "web/routes/database.py",
    "web/routes/config.py",
    "web/routes/assets.py",
    "web/routes/prompts.py",
    "web/routes/system.py",
)

PROJECT_ACTIVE_ROUTE_FILES = {
    "web/routes/projects.py": ("get_current_project",),
}

# Handlers intentionally global or cross-project (pid in path).
ROUTE_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "web/routes/database.py": ("get_runtime_logs", "clear_runtime_logs_api"),
    "web/routes/chapters/extras.py": ("save_feedback", "list_feedback", "golden_check"),
    "web/routes/chapters/chat.py": ("novel_chat_intro",),
    "web/routes/config.py": (
        "update_global_defaults",
        "get_setup_status",
        "get_config_schema",
    ),
    "web/routes/assets.py": (
        "list_assets",
        "list_presets",
        "list_components",
        "get_component",
        "get_preset",
        "create_preset",
        "delete_preset",
        "compose_preset",
    ),
    "web/routes/system.py": ("onboarding_status",),
    "web/routes/agent_api.py": (),
}


def _route_handlers(source: str) -> list[str]:
    return re.findall(
        r"@router\.(?:get|post|put|delete|patch)\([^)]+\)\s*\n(?:async )?def (\w+)",
        source,
    )


def test_project_scoped_routes_use_project_session() -> None:
    total = 0
    covered = 0
    for rel in PROJECT_SCOPED_ROUTE_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        exclusions = set(ROUTE_EXCLUSIONS.get(rel, ()))
        for name in _route_handlers(text):
            if name in exclusions:
                continue
            total += 1
            pattern = rf"(?:async )?def {name}\([^)]*ProjectSession"
            if re.search(pattern, text):
                covered += 1
    for rel, names in PROJECT_ACTIVE_ROUTE_FILES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for name in names:
            total += 1
            pattern = rf"(?:async )?def {name}\([^)]*ProjectSession"
            if re.search(pattern, text):
                covered += 1
    assert total > 0
    ratio = covered / total
    assert ratio >= 0.95, f"ProjectSession coverage {covered}/{total} = {ratio:.0%} (<95%)"


def test_deps_exports_session_helpers() -> None:
    text = (ROOT / "web" / "deps.py").read_text(encoding="utf-8")
    for marker in (
        "touch_project_activity",
        "current_project_info",
        "coerce_project_session",
        "task_manager_for",
        "ACTOR_HEADER",
        "actor_id",
    ):
        assert marker in text


def test_actor_header_resolves_on_request() -> None:
    from starlette.requests import Request

    from web.deps import ACTOR_HEADER, get_project_session

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(ACTOR_HEADER.lower().encode(), b"editor-1")],
    }
    request = Request(scope)
    session = get_project_session(request)
    assert session.actor_id == "editor-1"
