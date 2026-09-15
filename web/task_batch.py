"""Sequential chapter batch runner for TaskManager."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from novel_agent.domain.tasks import BatchOutcome, TaskStatus

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
    completed_chapters: Optional[List[str]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> BatchOutcome:
    completed = list(dict.fromkeys(str(item) for item in (completed_chapters or [])))
    child_task_ids: List[str] = []

    for ch in chapters:
        chapter_id = str(ch["chapter_id"])
        if chapter_id in completed:
            continue
        goal = ch["goal"]
        ch_dry_run = ch.get("dry_run", default_dry_run)

        if is_aborted(batch_id):
            return BatchOutcome(
                status=TaskStatus.CANCELLED,
                completed_chapters=completed,
                reason="user_abort",
                resumable_from=chapter_id,
                child_task_ids=child_task_ids,
            )

        try:
            task_id = await submit_chapter(chapter_id, goal, ch_dry_run)
            child_task_ids.append(task_id)
            async_task = running_tasks.get(task_id)
            if async_task:
                await async_task

            task = await get_task_async(task_id)
            status = str((task or {}).get("status") or "").strip().lower()
            if status in {"completed", "succeeded"}:
                completed.append(chapter_id)
                if on_progress is not None:
                    on_progress(
                        {
                            "step": "chapter_batch",
                            "chapter_id": chapter_id,
                            "current_chapter": chapter_id,
                            "completed_chapters": list(completed),
                            "child_task_ids": list(child_task_ids),
                            "total_chapters": len(chapters),
                        }
                    )
                continue

            reason = str(
                (task or {}).get("status_reason")
                or (task or {}).get("error")
                or (task or {}).get("_error")
                or status
                or "child_task_missing"
            )
            if status == "paused":
                logger.info("Batch %s paused at child task %s", batch_id, task_id)
                return BatchOutcome(
                    status=TaskStatus.PAUSED,
                    completed_chapters=completed,
                    failed_chapter=chapter_id,
                    reason=reason,
                    resumable_from=chapter_id,
                    child_task_ids=child_task_ids,
                )
            if status in {"cancelled", "aborted"} or is_aborted(task_id):
                logger.warning("Batch %s cancelled at child task %s", batch_id, task_id)
                return BatchOutcome(
                    status=TaskStatus.CANCELLED,
                    completed_chapters=completed,
                    failed_chapter=chapter_id,
                    reason=reason or "child_cancelled",
                    resumable_from=chapter_id,
                    child_task_ids=child_task_ids,
                )

            logger.warning(
                "Batch %s failed at child task %s (status=%s)",
                batch_id,
                task_id,
                status or "missing",
            )
            return BatchOutcome(
                status=TaskStatus.FAILED,
                completed_chapters=completed,
                failed_chapter=chapter_id,
                reason=reason,
                resumable_from=chapter_id,
                child_task_ids=child_task_ids,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Batch %s failed at chapter %s: %s", batch_id, chapter_id, exc)
            return BatchOutcome(
                status=TaskStatus.FAILED,
                completed_chapters=completed,
                failed_chapter=chapter_id,
                reason=str(exc),
                resumable_from=chapter_id,
                child_task_ids=child_task_ids,
            )

    return BatchOutcome(
        status=TaskStatus.SUCCEEDED,
        completed_chapters=completed,
        reason="completed",
        child_task_ids=child_task_ids,
    )
