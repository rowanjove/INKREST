from __future__ import annotations

import asyncio
from typing import Any

from novel_agent.domain.tasks import TaskStatus
from web.task_batch import run_chapter_batch


def test_batch_returns_failed_outcome_when_child_fails() -> None:
    submitted: list[str] = []

    async def submit_chapter(chapter_id: str, *_: Any) -> str:
        submitted.append(chapter_id)
        return f"task-{chapter_id}"

    async def get_task(_: str) -> dict[str, str]:
        return {"status": "failed", "error": "planner failed"}

    outcome = asyncio.run(
        run_chapter_batch(
            batch_id="batch-1",
            chapters=[
                {"chapter_id": "001", "goal": "first"},
                {"chapter_id": "002", "goal": "second"},
            ],
            default_dry_run=True,
            submit_chapter=submit_chapter,
            get_task_async=get_task,
            running_tasks={},
            is_aborted=lambda _: False,
        )
    )

    assert outcome.status == TaskStatus.FAILED
    assert outcome.completed_chapters == []
    assert outcome.resumable_from == "001"
    assert submitted == ["001"]


def test_batch_returns_paused_outcome_and_does_not_submit_next_child() -> None:
    submitted: list[str] = []

    async def submit_chapter(chapter_id: str, *_: Any) -> str:
        submitted.append(chapter_id)
        return f"task-{chapter_id}"

    async def get_task(_: str) -> dict[str, str]:
        return {"status": "paused", "status_reason": "user_pause"}

    outcome = asyncio.run(
        run_chapter_batch(
            batch_id="batch-2",
            chapters=[
                {"chapter_id": "001", "goal": "first"},
                {"chapter_id": "002", "goal": "second"},
            ],
            default_dry_run=True,
            submit_chapter=submit_chapter,
            get_task_async=get_task,
            running_tasks={},
            is_aborted=lambda _: False,
        )
    )

    assert outcome.status == TaskStatus.PAUSED
    assert outcome.resumable_from == "001"
    assert submitted == ["001"]


def test_batch_resume_skips_completed_chapters_and_emits_checkpoint() -> None:
    submitted: list[str] = []
    checkpoints: list[dict[str, Any]] = []

    async def submit_chapter(chapter_id: str, *_: Any) -> str:
        submitted.append(chapter_id)
        return f"task-{chapter_id}"

    async def get_task(_: str) -> dict[str, str]:
        return {"status": "completed"}

    outcome = asyncio.run(
        run_chapter_batch(
            batch_id="batch-3",
            chapters=[
                {"chapter_id": "001", "goal": "first"},
                {"chapter_id": "002", "goal": "second"},
            ],
            default_dry_run=True,
            submit_chapter=submit_chapter,
            get_task_async=get_task,
            running_tasks={},
            is_aborted=lambda _: False,
            completed_chapters=["001"],
            on_progress=checkpoints.append,
        )
    )

    assert outcome.status == TaskStatus.SUCCEEDED
    assert outcome.completed_chapters == ["001", "002"]
    assert submitted == ["002"]
    assert checkpoints[-1]["completed_chapters"] == ["001", "002"]
    assert checkpoints[-1]["current_chapter"] == "002"
