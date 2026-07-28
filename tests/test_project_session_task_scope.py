from __future__ import annotations

import asyncio

import web.context as context
from novel_agent.domain.tasks import TaskType
from web.deps import ProjectSession
from web.routes.chapters.tasks import list_tasks


def test_task_routes_use_the_request_project_when_active_project_changes(tmp_path):
    original_base = context.BASE_DIR
    original_active = context._active_project_id
    original_override = context._task_manager
    projects = tmp_path / "projects"
    root_a = projects / "book-a"
    root_b = projects / "book-b"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)
    try:
        context.BASE_DIR = tmp_path
        context._active_project_id = "book-b"
        context._task_manager = None
        manager_a = context._task_registry.get(root_a)
        manager_b = context._task_registry.get(root_b)
        manager_a._create_task_record(
            "task-a",
            TaskType.CHAPTER,
            {"chapter_id": "001", "goal": "A"},
        )
        manager_b._create_task_record(
            "task-b",
            TaskType.CHAPTER,
            {"chapter_id": "002", "goal": "B"},
        )

        result = asyncio.run(
            list_tasks(ProjectSession(project_id="book-a", root_dir=root_a))
        )

        assert [task.task_id for task in result] == ["task-a"]
    finally:
        context._task_registry.drop(root_a)
        context._task_registry.drop(root_b)
        context.BASE_DIR = original_base
        context._active_project_id = original_active
        context._task_manager = original_override
