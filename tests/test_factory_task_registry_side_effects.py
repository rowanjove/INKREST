from __future__ import annotations

from pathlib import Path

import web.context as context
from web.deps import ProjectSession
from web.project_task_registry import ProjectTaskRegistry
from web.routes.factory import _running_task_count


def test_factory_running_count_does_not_spawn_managers_for_idle_books(tmp_path: Path):
    original_base = context.BASE_DIR
    original_active = context._active_project_id
    original_override = context._task_manager
    registry = ProjectTaskRegistry.shared()

    projects = tmp_path / "projects"
    active = projects / "active-book"
    idle = projects / "idle-book"
    active.mkdir(parents=True)
    idle.mkdir(parents=True)

    try:
        context.BASE_DIR = tmp_path
        context._active_project_id = "active-book"
        context._task_manager = None

        # Ensure active manager exists so dashboard counting works for current book.
        registry.get(active)
        before = set(registry._managers)

        count = _running_task_count(
            ProjectSession(project_id="idle-book", root_dir=idle)
        )

        assert count == 0
        assert set(registry._managers) == before
        assert registry.peek(idle) is None
    finally:
        registry.drop(active)
        registry.drop(idle)
        context.BASE_DIR = original_base
        context._active_project_id = original_active
        context._task_manager = original_override
