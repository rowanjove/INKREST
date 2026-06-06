"""Progress emission for Electron IPC bridge.

When --json-output mode is active, each pipeline step emits a JSON line
to stdout so the Electron main process can parse and forward to the UI.
"""

import json
import sys
import time
from typing import Any, Dict, Optional

from novel_agent.logging_config import get_logger

logger = get_logger("progress")

_json_output_enabled = False
_progress_callback = None
_abort_check_callback = None


def register_abort_check(callback) -> None:
    """Register a callback to check if the current task has been aborted."""
    global _abort_check_callback
    _abort_check_callback = callback


def check_aborted() -> None:
    """Check if the task has been aborted, and raise TaskAbortedError if so."""
    if _abort_check_callback and _abort_check_callback():
        from novel_agent.exceptions import TaskAbortedError
        raise TaskAbortedError("任务已被用户中止。")


def enable_json_output() -> None:
    """Enable JSON progress output to stdout."""
    global _json_output_enabled
    _json_output_enabled = True


def is_json_output_enabled() -> bool:
    return _json_output_enabled


def register_progress_callback(callback) -> None:
    """Register a global callback to receive progress updates."""
    global _progress_callback
    _progress_callback = callback


def emit_progress(
    step: str,
    status: str,
    data: Optional[Dict[str, Any]] = None,
    chapter_id: str = "",
) -> None:
    """Emit a progress message.

    Args:
        step: Pipeline step name (e.g. 'planner', 'writer', 'auditor').
        status: One of 'running', 'done', 'error', 'skipped'.
        data: Optional payload (scene count, word count, etc).
        chapter_id: Current chapter being processed.
    """
    check_aborted()
    msg = {
        "type": "progress",
        "step": step,
        "status": status,
        "chapter_id": chapter_id,
        "timestamp": time.time(),
    }
    if data:
        msg["data"] = data

    if _json_output_enabled:
        try:
            print(json.dumps(msg, ensure_ascii=False), flush=True)
        except Exception as exc:
            logger.warning("Failed to print progress to stdout: %s", exc)

    if _progress_callback:
        try:
            _progress_callback(msg)
        except Exception as exc:
            logger.warning("Progress callback failed: %s", exc)

    logger.info("Progress: step=%s status=%s", step, status)


def emit_log(level: str, message: str, step: str = "", chapter_id: str = "") -> None:
    """Emit a log message to stdout in JSON mode and optional server/UI callbacks."""
    msg = {
        "type": "log",
        "level": level,
        "message": message,
        "step": step,
        "chapter_id": chapter_id,
        "timestamp": time.time(),
    }
    if _json_output_enabled:
        try:
            print(json.dumps(msg, ensure_ascii=False), flush=True)
        except Exception as exc:
            logger.warning("Failed to print log to stdout: %s", exc)

    if _progress_callback:
        try:
            _progress_callback(msg)
        except Exception as exc:
            logger.warning("Log callback failed: %s", exc)


def emit_complete(chapter_id: str, result: Optional[Dict[str, Any]] = None) -> None:
    """Emit a completion message."""
    msg = {
        "type": "complete",
        "chapter_id": chapter_id,
        "timestamp": time.time(),
    }
    if result:
        msg["result"] = result

    if _json_output_enabled:
        try:
            print(json.dumps(msg, ensure_ascii=False), flush=True)
        except Exception as exc:
            logger.warning("Failed to print completion to stdout: %s", exc)

    if _progress_callback:
        try:
            _progress_callback(msg)
        except Exception as exc:
            logger.warning("Completion callback failed: %s", exc)

    logger.info("Chapter %s completed", chapter_id)


def emit_hook_warning(
    hook_name: str,
    error: str,
    chapter_id: str = "",
) -> None:
    """Surface plugin hook failures to task progress / UI."""
    emit_progress(
        "plugin_hook",
        "warning",
        {"hook": hook_name, "error": error},
        chapter_id,
    )


def emit_error(chapter_id: str, error: str, step: str = "") -> None:
    """Emit an error message."""
    msg = {
        "type": "error",
        "chapter_id": chapter_id,
        "step": step,
        "error": error,
        "timestamp": time.time(),
    }
    if _json_output_enabled:
        try:
            print(json.dumps(msg, ensure_ascii=False), flush=True)
        except Exception as exc:
            logger.warning("Failed to print error to stdout: %s", exc)

    if _progress_callback:
        try:
            _progress_callback(msg)
        except Exception as exc:
            logger.warning("Error callback failed: %s", exc)

    logger.error("Chapter %s error at step %s: %s", chapter_id, step, error)
