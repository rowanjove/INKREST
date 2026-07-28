"""Unified write path for chapter / batch progress counters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from novel_agent.services.arc_queue import load_arc_progress, save_arc_progress
from novel_agent.services.chapter_highwater import bump_chapter_written, sync_highwater_from_store


def _ledger_ids(data: Dict[str, Any]) -> Set[str]:
    raw = data.get("completed_chapter_ids") or []
    if not isinstance(raw, list):
        return set()
    return {str(x).strip() for x in raw if str(x).strip()}


def record_chapter_success(root_dir: Path, chapter_id: str, *, pipeline_complete: bool = True) -> None:
    """
    Single write hook after a chapter finishes without batch failure.
    Keeps novel_batch_progress.completed_chapters aligned with completed_chapter_ids ledger.
    """
    cid = str(chapter_id).strip()
    if not cid:
        return

    bump_chapter_written(root_dir, cid, pipeline_complete=pipeline_complete)

    if not pipeline_complete:
        return

    data = load_arc_progress(root_dir)
    ledger = _ledger_ids(data)
    if cid not in ledger:
        ledger.add(cid)
        ordered: List[str] = sorted(ledger, key=lambda x: (len(x), x))
        data["completed_chapter_ids"] = ordered
        data["completed_chapters"] = len(ordered)
        save_arc_progress(root_dir, data)

    try:
        sync_highwater_from_store(root_dir)
    except Exception:
        pass


def reconcile_progress_ledger(root_dir: Path) -> Dict[str, Any]:
    """Rebuild ledger from checkpoints with post_audit (repair drift)."""
    chapters_root = root_dir / "workspace" / "chapters"
    found: Set[str] = set()
    if chapters_root.is_dir():
        import json

        for d in chapters_root.glob("chapter_*"):
            cp = d / "checkpoint.json"
            if not cp.is_file():
                continue
            try:
                row = json.loads(cp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if "post_audit" in (row.get("completed_stages") or []):
                cid = str(row.get("chapter_id") or d.name.replace("chapter_", ""))
                if cid:
                    found.add(cid)

    data = load_arc_progress(root_dir)
    data["completed_chapter_ids"] = sorted(found, key=lambda x: (len(x), x))
    data["completed_chapters"] = len(found)
    save_arc_progress(root_dir, data)
    return data