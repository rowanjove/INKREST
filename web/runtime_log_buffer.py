"""In-memory ring buffer for Agent / pipeline runtime logs (UI + 山山助手)."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

_MAX_ENTRIES = 500
_buffer: Deque[Dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)
_lock = Lock()
_seq = 0


def _normalize_ts(raw: Any) -> float:
    if raw is None:
        return time.time()
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return time.time()
    # epoch seconds vs milliseconds
    if val > 1e12:
        return val / 1000.0
    return val


def append_runtime_log(entry: Dict[str, Any]) -> int:
    """Append one log line; returns monotonic id."""
    global _seq
    msg_type = str(entry.get("type") or "log")
    level = str(entry.get("level") or "info").lower()
    step = str(entry.get("step") or "")
    chapter_id = str(entry.get("chapter_id") or "")
    message = str(entry.get("message") or entry.get("error") or "")

    status = str(entry.get("status") or "")
    if msg_type == "progress" and not message:
        message = f"{step} · {status}" if step else status
        if status in ("error", "blocked"):
            level = "error"
        elif status in ("warning",):
            level = "warn"
    elif msg_type == "error" and not message:
        message = str(entry.get("error") or "任务错误")
        level = "error"
    elif msg_type == "complete" and not message:
        message = f"章节 {chapter_id} 完成" if chapter_id else "任务完成"
        level = "info"

    if not message.strip():
        return _seq

    with _lock:
        _seq += 1
        item = {
            "id": _seq,
            "timestamp": _normalize_ts(entry.get("timestamp")),
            "level": level,
            "step": step,
            "message": message.strip(),
            "chapter_id": chapter_id,
            "source": str(entry.get("source") or "agent"),
            "type": msg_type,
            "project_id": str(entry.get("project_id") or ""),
            "task_id": str(entry.get("task_id") or ""),
        }
        if msg_type == "progress" and status:
            item["status"] = status
        _buffer.append(item)
        return _seq


def list_runtime_logs(
    since_id: int = 0,
    limit: int = 200,
    *,
    project_id: str | None = None,
) -> List[Dict[str, Any]]:
    with _lock:
        rows = [
            dict(x)
            for x in _buffer
            if int(x.get("id") or 0) > since_id
            and (project_id is None or str(x.get("project_id") or "") == project_id)
        ]
    if limit > 0 and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def tail_runtime_logs(
    limit: int = 80,
    *,
    project_id: str | None = None,
) -> List[Dict[str, Any]]:
    with _lock:
        rows = [
            dict(x)
            for x in _buffer
            if project_id is None or str(x.get("project_id") or "") == project_id
        ]
    if limit > 0 and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def clear_runtime_logs(*, project_id: str | None = None) -> None:
    """Clear every log for tests/maintenance, or only one project's UI logs."""
    global _seq
    with _lock:
        if project_id is None:
            _buffer.clear()
            _seq = 0
            return
        retained = [
            item
            for item in _buffer
            if str(item.get("project_id") or "") != project_id
        ]
        _buffer.clear()
        _buffer.extend(retained)


def read_system_log_tail(log_path: Optional[Any], max_lines: int = 60) -> List[str]:
    """Read last lines from novel_agent.log (JSON or plain)."""
    if not log_path:
        return []
    try:
        path = log_path if hasattr(log_path, "read_text") else None
        if path is None or not path.is_file():
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines[-max_lines:]
    except Exception:
        return []
