"""Map pipeline progress events to task DB updates and runtime logs."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict

_PROGRESS_DEBOUNCE_SEC = 0.5
_PROGRESS_CACHE_MAX = 2000
_last_progress_write: Dict[str, float] = {}


def _prune_progress_cache() -> None:
    if len(_last_progress_write) <= _PROGRESS_CACHE_MAX:
        return
    stale_keys = sorted(_last_progress_write, key=_last_progress_write.get)
    for key in stale_keys[: len(_last_progress_write) - _PROGRESS_CACHE_MAX]:
        _last_progress_write.pop(key, None)


def _should_write_progress(task_id: str, msg: Dict[str, Any]) -> bool:
    step = str(msg.get("step") or "")
    status = str(msg.get("status") or "")
    # Terminal states must always persist — debouncing them leaves the UI stuck on "running".
    if status in ("done", "error", "blocked", "skipped", "warning"):
        key = f"{task_id}:{step}"
        _last_progress_write[key] = time.monotonic()
        return True
    key = f"{task_id}:{step}"
    now = time.monotonic()
    last = _last_progress_write.get(key, 0.0)
    if now - last < _PROGRESS_DEBOUNCE_SEC:
        return False
    _last_progress_write[key] = now
    _prune_progress_cache()
    return True


def handle_progress_message(
    msg: Dict[str, Any],
    *,
    root_exists: Callable[[], bool],
    update_task_progress: Callable[[str, Dict[str, Any]], None],
    update_task_chapter_id: Callable[[str, str], None],
    append_task_log: Callable[[str, Dict[str, Any]], None],
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
    task_id = str(msg.get("task_id") or "")

    if not task_id:
        return

    wrote = False
    should_persist_log = msg_type in {"log", "error"}
    try:
        loop = asyncio.get_running_loop()
        if msg_type == "progress":
            if _should_write_progress(task_id, msg):
                loop.run_in_executor(None, update_task_progress, task_id, msg)
                wrote = True
        elif msg_type == "complete" and chapter_id:
            loop.run_in_executor(None, update_task_chapter_id, task_id, chapter_id)
            wrote = True
        if wrote or should_persist_log:
            loop.run_in_executor(None, append_task_log, task_id, msg)
    except RuntimeError:
        if msg_type == "progress":
            if _should_write_progress(task_id, msg):
                update_task_progress(task_id, msg)
                wrote = True
        elif msg_type == "complete" and chapter_id:
            update_task_chapter_id(task_id, chapter_id)
            wrote = True
        if wrote or should_persist_log:
            append_task_log(task_id, msg)

    try:
        from web.task_ws_hub import broadcast_progress
        broadcast_progress(msg)
    except Exception:
        pass

    if wrote:
        try:
            from web.task_ws_hub import notify_tasks_changed

            notify_tasks_changed()
        except Exception:
            pass
