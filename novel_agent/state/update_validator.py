"""Validate and sanitize LLM-produced state_update payloads before persistence."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,128}$")
MAX_TEXT_LEN = 20_000

ALLOWED_TOP_LEVEL: Set[str] = {
    "events",
    "objects",
    "threads",
    "characters",
    "timeline_nodes",
    "timeline_edges",
    "foreshadows",
    "hooks",
    "reader_promises",
    "secrets",
    "character_relations",
    "character_memories",
    "character_behaviors",
}

LIST_ENTITY_KEYS = (
    "events",
    "objects",
    "threads",
    "timeline_nodes",
    "timeline_edges",
    "foreshadows",
    "hooks",
    "reader_promises",
    "secrets",
    "character_relations",
    "character_memories",
    "character_behaviors",
)


class StateUpdateValidationError(ValueError):
    """Raised when state_update cannot be safely applied."""


def _safe_id(value: Any, field: str) -> str:
    if value is None:
        import uuid
        return f"auto_{uuid.uuid4().hex[:8]}"
    text = str(value).strip()
    # 支持中文、英文字母、数字、下划线、连字符、点和冒号
    # 自动将其他不支持的特殊字符（如空格、引号等）替换为下划线，保障流水线健壮性，不直接抛出异常
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.:\u4e00-\u9fa5]", "_", text)
    if not cleaned:
        import uuid
        cleaned = f"auto_{uuid.uuid4().hex[:8]}"
    return cleaned


def _truncate_text(value: Any, max_len: int = MAX_TEXT_LEN) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > max_len:
        return text[:max_len]
    return text


def _sanitize_list_items(items: Any, chapter_id: str, require_id: bool = True) -> List[Dict[str, Any]]:
    if not items:
        return []
    if not isinstance(items, list):
        raise StateUpdateValidationError("Expected list entity payload")
    cleaned: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if require_id and row.get("id"):
            row["id"] = _safe_id(row["id"], "entity")
        if "summary" in row:
            row["summary"] = _truncate_text(row.get("summary"))
        if "description" in row:
            row["description"] = _truncate_text(row.get("description"))
        if "chapter_id" in row and row["chapter_id"]:
            row["chapter_id"] = str(row["chapter_id"])
        elif chapter_id:
            row.setdefault("chapter_id", chapter_id)
        cleaned.append(row)
    return cleaned


def _safe_character_key(name: Any) -> str:
    text = str(name).strip()
    if not text or len(text) > 64:
        raise StateUpdateValidationError(f"Invalid character name: {name!r}")
    if ".." in text or "/" in text or "\\" in text:
        raise StateUpdateValidationError(f"Invalid character name: {name!r}")
    return text


def _sanitize_characters(characters: Any) -> Dict[str, Any]:
    if not characters:
        return {}
    if not isinstance(characters, dict):
        raise StateUpdateValidationError("characters must be a dict")
    cleaned: Dict[str, Any] = {}
    for name, state in characters.items():
        key = _safe_character_key(name)
        if isinstance(state, dict):
            cleaned[key] = {
                k: (_truncate_text(v) if isinstance(v, str) else v)
                for k, v in state.items()
            }
        else:
            cleaned[key] = state
    return cleaned


def _filter_cross_chapter_events(
    db_path: Optional[Path],
    chapter_id: str,
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not db_path or not db_path.exists() or not events:
        return events
    owned: Dict[str, str] = {}
    event_ids = []
    for event in events:
        if event.get("id"):
            try:
                event_ids.append(_safe_id(event["id"], "event"))
            except StateUpdateValidationError:
                continue
    if not event_ids:
        return events
    placeholders = ",".join("?" for _ in event_ids)
    query = f"select id, chapter_id from events where id in ({placeholders})"
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        for row in conn.execute(query, event_ids):
            owned[str(row[0])] = str(row[1] or "")

    kept: List[Dict[str, Any]] = []
    for event in events:
        eid = event.get("id")
        if not eid:
            kept.append(event)
            continue
        try:
            safe_id = _safe_id(eid, "event")
        except StateUpdateValidationError:
            continue
        existing_chapter = owned.get(safe_id)
        if existing_chapter and existing_chapter != str(chapter_id):
            continue
        kept.append(event)
    return kept


def validate_state_update(
    chapter_id: str,
    update: Dict[str, Any],
    *,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return a sanitized copy of ``update`` safe to pass to ``sync_state_update``."""
    if not chapter_id or not str(chapter_id).strip():
        raise StateUpdateValidationError("chapter_id is required")
    if not isinstance(update, dict):
        raise StateUpdateValidationError("state_update must be a dict")

    sanitized: Dict[str, Any] = {}
    for key, value in update.items():
        if key not in ALLOWED_TOP_LEVEL:
            continue
        if key in LIST_ENTITY_KEYS:
            sanitized[key] = _sanitize_list_items(value, chapter_id, require_id=(key != "character_memories"))
        elif key == "characters":
            sanitized[key] = _sanitize_characters(value)
        else:
            sanitized[key] = value

    events = sanitized.get("events") or []
    sanitized["events"] = _filter_cross_chapter_events(db_path, str(chapter_id), events)
    return sanitized
