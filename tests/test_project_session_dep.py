"""Contract: high-risk routes use ProjectSession dependency injection."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Project-scoped generation/outline/task routes (excludes global /api/projects CRUD).
HIGH_RISK_ROUTE_FILES = (
    "web/routes/factory.py",
    "web/routes/chapters/tasks.py",
    "web/routes/chapters/crud.py",
    "web/routes/outlines.py",
    "web/routes/assistant.py",
    "web/routes/agent_api.py",
)

PROJECT_ACTIVE_ROUTE_FILES = {
    "web/routes/projects.py": ("get_current_project",),
}

_SESSION_MARKERS = (
    "ProjectSession",
    "RequireProjectDep",
    "get_project_session",
    "Depends(get_project_session)",
)


def _route_handlers(source: str) -> list[str]:
    return re.findall(r"@router\.(?:get|post|put|delete|patch)\([^)]+\)\s*\n(?:async )?def (\w+)", source)


def test_high_risk_routes_use_project_session() -> None:
    total = 0
    covered = 0
    for rel in HIGH_RISK_ROUTE_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for name in _route_handlers(text):
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
    assert ratio >= 0.8, f"ProjectSession coverage {covered}/{total} = {ratio:.0%} (<80%)"


def test_deps_exports_session_helpers() -> None:
    text = (ROOT / "web" / "deps.py").read_text(encoding="utf-8")
    for marker in ("touch_project_activity", "current_project_info", "coerce_project_session"):
        assert marker in text