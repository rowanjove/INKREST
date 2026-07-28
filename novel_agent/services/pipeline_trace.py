"""Per-chapter pipeline trace for debugging cost/latency (pipeline_trace.json)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def trace_path(chapter_dir: Path) -> Path:
    return chapter_dir / "reports" / "pipeline_trace.json"


def load_trace(chapter_dir: Path) -> List[Dict[str, Any]]:
    path = trace_path(chapter_dir)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events") if isinstance(data, dict) else data
        return list(events) if isinstance(events, list) else []
    except Exception:
        return []


def append_trace_event(
    chapter_dir: Path,
    *,
    step: str,
    status: str,
    chapter_id: str = "",
    data: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> None:
    reports = chapter_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    events = load_trace(chapter_dir)
    entry: Dict[str, Any] = {
        "step": step,
        "status": status,
        "chapter_id": chapter_id,
        "ts": time.time(),
    }
    if data:
        entry["data"] = data
    if duration_ms is not None:
        entry["duration_ms"] = round(duration_ms, 1)
    events.append(entry)
    path = trace_path(chapter_dir)
    path.write_text(
        json.dumps({"events": events[-200:]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )