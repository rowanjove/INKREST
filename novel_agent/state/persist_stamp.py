"""Idempotency stamps for chapter post_audit persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def compute_persist_stamp(chapter_id: str, final_text: str, state_update: Dict[str, Any]) -> str:
    event_ids = sorted(
        str(e.get("id"))
        for e in (state_update.get("events") or [])
        if isinstance(e, dict) and e.get("id")
    )
    payload = {
        "chapter_id": chapter_id,
        "final_chars": len((final_text or "").strip()),
        "event_ids": event_ids,
        "hook_count": len(state_update.get("hooks") or []),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_persist_stamp(stamp_path: Path) -> str:
    if not stamp_path.exists():
        return ""
    try:
        data = json.loads(stamp_path.read_text(encoding="utf-8"))
        return str(data.get("stamp") or "")
    except (json.JSONDecodeError, OSError):
        return ""


def write_persist_stamp(stamp_path: Path, stamp: str, chapter_id: str) -> None:
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(
        json.dumps({"chapter_id": chapter_id, "stamp": stamp}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
