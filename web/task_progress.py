"""Map pipeline progress events to task DB updates and runtime logs."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional

_PROGRESS_DEBOUNCE_SEC = 0.5
_last_progress_write: Dict[str, float] = {}


def _should_write_progress(task_id: str, msg: Dict[str, Any]) -> bool:
    step = str(msg.get("step") or "")
    key = f"{task_id}:{step}"
    now = time.monotonic()
    last = _last_progress_write.get(key, 0.0)
    if now - last < _PROGRESS_DEBOUNCE_SEC:
        return False
    _last_progress_write[key] = now
    return True


def handle_progress_message(
    msg: Dict[str, Any],
    *,
    root_exists: Callable[[], bool],
    running_chapters: Dict[str, str],
    running_tasks: Dict[str, Any],
    update_task_progress: Callable[[str, Dict[str, Any]], None],
    update_task_chapter_id: Callable[[str, str], None],
) -> None:
    if not root_exists():
        return

    try:
        from web.runtime_log_buffer import append_runtime_log

        append_runtime_log(msg)
    except Exception:
        pass

    msg_type = msg.get("type")
    chapter_id = msg.get("chapter_id")
    task_id: Optional[str] = None

    if chapter_id:
        task_id = running_chapters.get(chapter_id)
    if not task_id:
        for tid in running_tasks:
            if tid.startswith("novel-"):
                task_id = tid
                break
    if not task_id and msg_type in ("novel_autopilot", "novel_batch", "arc_batch"):
        for tid in running_tasks:
            if tid.startswith("novel-auto") or tid.startswith("novel-cont"):
                task_id = tid
                break

    if not task_id:
        return

    try:
        loop = asyncio.get_running_loop()
        if msg_type == "progress":
            if _should_write_progress(task_id, msg):
                loop.run_in_executor(None, update_task_progress, task_id, msg)
        elif msg_type == "complete" and task_id.startswith("novel-") and chapter_id:
            loop.run_in_executor(None, update_task_chapter_id, task_id, chapter_id)
    except RuntimeError:
        if msg_type == "progress":
            if _should_write_progress(task_id, msg):
                update_task_progress(task_id, msg)
        elif msg_type == "complete" and task_id.startswith("novel-") and chapter_id:
            update_task_chapter_id(task_id, chapter_id)