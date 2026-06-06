"""Single source for novel progress metrics (library vs batch vs disk)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from novel_agent.services.arc_queue import load_arc_progress
from novel_agent.services.pipeline_pending import summarize_pipeline_pending


def _count_disk_chapters_with_final(root: Path) -> int:
    chapters_root = root / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return 0
    n = 0
    for d in chapters_root.glob("chapter_*"):
        final = d / "chapter_final.txt"
        if final.is_file() and final.read_text(encoding="utf-8").strip():
            n += 1
    return n


def _remaining_chapters(root: Path, authoritative_completed: int) -> int:
    outline_path = root / "workspace" / "outline.json"
    if not outline_path.is_file():
        return 0
    try:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    prof = outline.get("scale_profile") or {}
    scale = str(prof.get("scale") or "")
    hard_max = int(prof.get("max_chapters") or 0)
    limit = int(outline.get("target_chapters") or hard_max or 20)
    cap = limit if hard_max >= 999999 or scale == "infinite" else min(limit, hard_max or limit)
    return max(0, cap - authoritative_completed)


def _count_pipeline_complete_on_disk(root: Path) -> int:
    chapters_root = root / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return 0
    n = 0
    for d in chapters_root.glob("chapter_*"):
        cp = d / "checkpoint.json"
        if not cp.is_file():
            continue
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        stages = data.get("completed_stages") or []
        if "post_audit" in stages and not data.get("resolved_at"):
            n += 1
        elif "post_audit" in stages:
            n += 1
    return n


def build_progress_summary(root: Path, *, reconcile: bool = False) -> Dict[str, Any]:
    if reconcile:
        try:
            from novel_agent.services.progress_sync import reconcile_progress_ledger

            reconcile_progress_ledger(root)
        except Exception:
            pass
    progress = load_arc_progress(root)
    authoritative_completed = int(progress.get("completed_chapters") or 0)
    ledger = progress.get("completed_chapter_ids") or []

    library_indexed = 0
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        library_indexed = SQLiteStateStore(root).count_chapters()
    except Exception:
        library_indexed = 0

    disk_with_final = _count_disk_chapters_with_final(root)
    disk_pipeline_complete = _count_pipeline_complete_on_disk(root)
    pending = summarize_pipeline_pending(root)

    remaining_chapters = _remaining_chapters(root, authoritative_completed)

    return {
        "authoritative_completed": authoritative_completed,
        "completed_chapter_ids": ledger if isinstance(ledger, list) else [],
        "library_indexed": library_indexed,
        "disk_chapters_with_final": disk_with_final,
        "disk_pipeline_complete": disk_pipeline_complete,
        "pending_total": pending.get("pending_total", 0),
        "pending_retry_count": pending.get("pending_retry_count", 0),
        "pending_gate_count": pending.get("pending_gate_count", 0),
        "batch_status": progress.get("status", "idle"),
        "batch_paused": progress.get("status") == "paused",
        "pause_reason": progress.get("pause_reason", ""),
        "last_arc_id": progress.get("last_arc_id", ""),
        "last_chapter_id": progress.get("last_chapter_id", ""),
        "fail_streak": int(progress.get("fail_streak") or 0),
        "remaining_chapters": remaining_chapters,
        "progress_note": (
            "续跑与熔断以 novel_batch_progress.completed_chapters 为准；"
            "书库章数为索引口径；待处理以 pending_total 为准。"
        ),
    }