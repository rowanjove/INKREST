"""Sequential chapter batch runner for TaskManager."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("tasks.batch")


async def run_chapter_batch(
    batch_id: str,
    chapters: List[Dict[str, Any]],
    default_dry_run: bool,
    *,
    submit_chapter: Callable[..., Awaitable[str]],
    get_task_async: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
    is_aborted: Callable[[str], bool],
    running_tasks: Dict[str, Any],
) -> None:
    for ch in chapters:
        chapter_id = ch["chapter_id"]
        goal = ch["goal"]
        ch_dry_run = ch.get("dry_run", default_dry_run)

        try:
            task_id = await submit_chapter(chapter_id, goal, ch_dry_run)
            async_task = running_tasks.get(task_id)
            if async_task:
                await async_task

            task = await get_task_async(task_id)
            if task and (task.get("status") == "failed" or is_aborted(task_id)):
                logger.warning("Batch %s halted: task %s failed/aborted", batch_id, task_id)
                break
        except Exception as exc:
            logger.error("Batch %s failed at chapter %s: %s", batch_id, chapter_id, exc)
            break
    running_tasks.pop(batch_id, None)
