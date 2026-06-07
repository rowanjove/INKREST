"""Persist chapters skipped during novel batch runs (exceptions / gate failures)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

QUEUE_PATH_REL = "workspace/reports/batch_retry_queue.json"


def _queue_path(root_dir: Path) -> Path:
    return root_dir / QUEUE_PATH_REL


def _load_doc(root_dir: Path) -> Dict[str, Any]:
    path = _queue_path(root_dir)
    if not path.is_file():
        return {"items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"items": []}
    except (json.JSONDecodeError, OSError):
        return {"items": []}


def _save_doc(root_dir: Path, doc: Dict[str, Any]) -> None:
    path = _queue_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from novel_agent.services.pipeline_pending import invalidate_pipeline_alerts_cache

        invalidate_pipeline_alerts_cache(root_dir)
    except Exception:
        pass


def record_batch_retry(
    root_dir: Path,
    *,
    chapter_id: str,
    arc_id: str = "",
    reason: str = "run_chapter_error",
    step: str = "run_chapter",
    message: str = "",
) -> Dict[str, Any]:
    """Upsert a pending retry entry for chapter_id."""
    cid = str(chapter_id or "").strip()
    if not cid:
        return {}
    doc = _load_doc(root_dir)
    items: List[Dict[str, Any]] = list(doc.get("items") or [])
    now = datetime.now().isoformat()
    entry = {
        "chapter_id": cid,
        "arc_id": str(arc_id or ""),
        "reason": reason,
        "step": step,
        "message": (message or "")[:500],
        "timestamp": now,
        "resolved_at": None,
        "attempt_count": 1,
    }
    replaced = False
    for i, row in enumerate(items):
        if str(row.get("chapter_id")) == cid and not row.get("resolved_at"):
            prev_attempts = int(row.get("attempt_count") or 1)
            entry["attempt_count"] = prev_attempts + 1
            items[i] = {**row, **entry}
            replaced = True
            break
    if not replaced:
        items.append(entry)
    doc["items"] = items[-200:]
    _save_doc(root_dir, doc)
    return entry


def get_chapter_attempt_count(root_dir: Path, chapter_id: str) -> int:
    """Pending retry attempts for chapter_id (0 if none)."""
    cid = str(chapter_id or "").strip()
    for row in list_pending_retries(root_dir):
        if str(row.get("chapter_id")) == cid:
            return int(row.get("attempt_count") or 1)
    return 0


def list_pending_retries(root_dir: Path) -> List[Dict[str, Any]]:
    items = _load_doc(root_dir).get("items") or []
    pending = [i for i in items if isinstance(i, dict) and not i.get("resolved_at")]
    pending.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return pending


def dismiss_batch_retry(root_dir: Path, chapter_id: str) -> bool:
    cid = str(chapter_id or "").strip()
    doc = _load_doc(root_dir)
    items: List[Dict[str, Any]] = list(doc.get("items") or [])
    found = False
    now = datetime.now().isoformat()
    for row in items:
        if str(row.get("chapter_id")) == cid and not row.get("resolved_at"):
            row["resolved_at"] = now
            found = True
    if found:
        doc["items"] = items
        _save_doc(root_dir, doc)
    return found


def clear_resolved_retries(root_dir: Path, *, keep_last: int = 50) -> int:
    """Drop old resolved entries; return number removed."""
    doc = _load_doc(root_dir)
    items: List[Dict[str, Any]] = list(doc.get("items") or [])
    pending = [i for i in items if not i.get("resolved_at")]
    resolved = sorted(
        [i for i in items if i.get("resolved_at")],
        key=lambda x: str(x.get("resolved_at") or ""),
        reverse=True,
    )[:keep_last]
    removed = len(items) - len(pending) - len(resolved)
    doc["items"] = pending + resolved
    _save_doc(root_dir, doc)
    return max(0, removed)