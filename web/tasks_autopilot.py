"""Helper module to run novel continue and autopilot tasks asynchronously."""

import asyncio
import uuid
import logging
from typing import Any, Dict, List, Optional
from novel_agent.pipeline import PipelineConfig
from novel_agent.orchestrator import NovelOrchestrator

logger = logging.getLogger("tasks.autopilot")

# Share task_id_var context variable from web.tasks
from web.tasks import task_id_var


def active_novel_batch_task_id_helper(task_manager) -> Optional[str]:
    for tid, task in task_manager._running_tasks.items():
        if (tid.startswith("novel-auto") or tid.startswith("novel-cont")) and not task.done():
            return tid
    try:
        for row in task_manager.store.list_tasks():
            tid = str(row.get("id") or "")
            if not (tid.startswith("novel-auto") or tid.startswith("novel-cont")):
                continue
            if str(row.get("status") or "") in ("pending", "running"):
                return tid
    except Exception:
        pass
    return None


async def submit_novel_continue_helper(
    task_manager,
    resume: bool = True,
    max_chapters: int = 0,
    dry_run: bool = False,
    *,
    autopilot: bool = False,
    full_book: bool = True,
    chapters_per_round: int = 0,
    max_rounds: int = 0,
) -> str:
    with task_manager._novel_batch_lock:
        active = active_novel_batch_task_id_helper(task_manager)
        if active:
            raise ValueError(
                f"Novel batch already running (task {active}). "
                "Wait for completion or abort before starting another continue."
            )
    prefix = "novel-auto" if autopilot else "novel-cont"
    label = "Novel autopilot" if autopilot else "Novel continue"
    task_id = f"{prefix}-{str(uuid.uuid4())[:8]}"
    await asyncio.get_running_loop().run_in_executor(
        None,
        task_manager.store.save_task,
        task_id,
        None,
        label,
        dry_run,
        "pending",
    )
    loop = asyncio.get_running_loop()
    if autopilot:
        task = loop.create_task(
            run_novel_autopilot_helper(
                task_manager,
                task_id,
                resume,
                max_chapters,
                dry_run,
                full_book=full_book,
                chapters_per_round=chapters_per_round,
                max_rounds=max_rounds,
            )
        )
    else:
        task = loop.create_task(
            run_novel_continue_helper(
                task_manager, task_id, resume, max_chapters, dry_run, full_book=full_book
            )
        )
    with task_manager._novel_batch_lock:
        if active_novel_batch_task_id_helper(task_manager):
            task.cancel()
            raise ValueError(
                f"Novel batch already running. "
                "Wait for completion or abort before starting another continue."
            )
        task_manager._running_tasks[task_id] = task
    return task_id


async def run_novel_autopilot_helper(
    task_manager,
    task_id: str,
    resume: bool,
    max_chapters: int,
    dry_run: bool,
    *,
    full_book: bool,
    chapters_per_round: int,
    max_rounds: int,
) -> None:
    token = task_id_var.set(task_id)
    try:
        await asyncio.wait_for(task_manager._semaphore_for_loop().acquire(), timeout=600)
    except asyncio.TimeoutError:
        await asyncio.get_running_loop().run_in_executor(
            None,
            task_manager.store.update_task_status,
            task_id,
            "failed",
            None,
            "Too many concurrent tasks.",
        )
        task_manager._running_tasks.pop(task_id, None)
        task_id_var.reset(token)
        return

    await asyncio.get_running_loop().run_in_executor(
        None, task_manager.store.update_task_status, task_id, "running"
    )
    try:
        from novel_agent.services.novel_autopilot import run_novel_autopilot

        await task_manager._ensure_llm_ready(dry_run)
        config = (
            PipelineConfig.dry_run(task_manager.root_dir)
            if dry_run
            else PipelineConfig.from_config(task_manager.root_dir)
        )
        orchestrator = NovelOrchestrator(config)
        if resume:
            from novel_agent.services.arc_queue import clear_batch_pause_for_resume

            clear_batch_pause_for_resume(task_manager.root_dir)
        outcome = await run_novel_autopilot(
            orchestrator,
            max_chapters=max_chapters,
            chapters_per_round=chapters_per_round,
            full_book=full_book,
            max_rounds=max_rounds,
        )
        if outcome.paused:
            status = "completed"
            payload = {
                "autopilot": True,
                "rounds": outcome.rounds,
                "chapters_completed": outcome.chapters_completed,
                "stopped_reason": outcome.stopped_reason,
                "paused": True,
                "circuit_breaker": True,
                "round_summaries": outcome.round_summaries,
                "message": "全书自动续跑因批量熔断暂停，请处理章节后于运行监控续跑。",
            }
        else:
            status = "completed"
            payload = {
                "autopilot": True,
                "rounds": outcome.rounds,
                "chapters_completed": outcome.chapters_completed,
                "stopped_reason": outcome.stopped_reason,
                "paused": False,
                "round_summaries": outcome.round_summaries,
            }
        await asyncio.get_running_loop().run_in_executor(
            None,
            task_manager.store.update_task_status,
            task_id,
            status,
            payload,
        )
    except Exception as exc:
        logger.exception("Novel autopilot %s failed: %s", task_id, exc)
        await task_manager._mark_task_failed(task_id, exc)
    finally:
        task_manager._semaphore_for_loop().release()
        task_manager._running_tasks.pop(task_id, None)
        task_id_var.reset(token)


async def run_novel_continue_helper(
    task_manager,
    task_id: str,
    resume: bool,
    max_chapters: int,
    dry_run: bool,
    *,
    full_book: bool = False,
) -> None:
    token = task_id_var.set(task_id)
    try:
        await asyncio.wait_for(task_manager._semaphore_for_loop().acquire(), timeout=600)
    except asyncio.TimeoutError:
        await asyncio.get_running_loop().run_in_executor(
            None,
            task_manager.store.update_task_status,
            task_id,
            "failed",
            None,
            "Too many concurrent tasks.",
        )
        task_manager._running_tasks.pop(task_id, None)
        task_id_var.reset(token)
        return

    await asyncio.get_running_loop().run_in_executor(
        None, task_manager.store.update_task_status, task_id, "running"
    )
    try:
        await task_manager._ensure_llm_ready(dry_run)
        config = PipelineConfig.dry_run(task_manager.root_dir) if dry_run else PipelineConfig.from_config(task_manager.root_dir)
        orchestrator = NovelOrchestrator(config)
        cap = int(max_chapters) if max_chapters and max_chapters > 0 else None
        results = await orchestrator.arun_novel_continue(
            resume=resume, max_chapters=cap, full_book=full_book
        )
        await asyncio.get_running_loop().run_in_executor(
            None,
            task_manager.store.update_task_status,
            task_id,
            "completed",
            {
                "chapters_completed": len(results),
                "full_book": full_book,
            },
        )
    except Exception as exc:
        logger.exception("Novel continue %s failed: %s", task_id, exc)
        await task_manager._mark_task_failed(task_id, exc)
    finally:
        task_manager._semaphore_for_loop().release()
        task_manager._running_tasks.pop(task_id, None)
        task_id_var.reset(token)
