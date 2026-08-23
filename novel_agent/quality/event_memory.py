"""Evidence-oriented projection of the existing narrative event state.

The project already persists extracted events in SQLite.  This module adds a
stable, source-aware projection on top of that payload without introducing a
second narrative source of truth.  It is intentionally tolerant of older event
records; missing fields remain explicit instead of being guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


NARRATIVE_EVENT_SCHEMA_VERSION = 1
_EVENT_FILENAME = "narrative_events.json"


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def _as_mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _event_id(event: Mapping[str, Any], chapter_id: str, index: int) -> str:
    raw = str(event.get("id") or "").strip()
    if raw:
        return raw
    digest = hashlib.sha256(
        f"{chapter_id}:{index}:{event.get('summary', '')}".encode("utf-8")
    ).hexdigest()[:12]
    return f"event_{chapter_id}_{digest}"


def _chapter_sort_value(chapter_id: Any) -> Optional[int]:
    match = re.search(r"\d+", str(chapter_id or ""))
    return int(match.group(0)) if match else None


def derive_event_revision_id(chapter_id: str, events: Sequence[Mapping[str, Any]]) -> str:
    """Derive a stable local revision when the upstream document has no ID."""

    raw = json.dumps(
        {"chapter_id": str(chapter_id), "events": list(events or [])},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return "events:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalise_narrative_event(
    event: Mapping[str, Any],
    *,
    chapter_id: str,
    index: int = 0,
    source_document_id: str = "",
    source_revision_id: str = "",
    source_span: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Map legacy extractor output to the evidence-oriented event contract."""

    payload = _as_mapping(event.get("payload"))
    merged: Dict[str, Any] = {**payload, **dict(event)}
    actors = _as_list(merged.get("actors") or merged.get("characters"))
    objects = _as_list(merged.get("objects") or merged.get("items"))
    causes = _as_list(merged.get("causes") or merged.get("predecessors"))
    effects = _as_list(merged.get("effects") or merged.get("consequences"))
    knower_ids = _as_list(merged.get("knower_ids") or merged.get("knowers"))
    state_delta = _as_mapping(merged.get("state_delta") or merged.get("stateDelta"))
    confidence = merged.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "schema_version": NARRATIVE_EVENT_SCHEMA_VERSION,
        "id": _event_id(merged, chapter_id, index),
        "chapter_id": str(merged.get("chapter_id") or chapter_id),
        "scene_id": str(merged.get("scene_id") or ""),
        "story_time": merged.get("story_time") or merged.get("time") or "",
        "story_time_start": merged.get("story_time_start") or merged.get("storyTimeStart") or "",
        "story_time_end": merged.get("story_time_end") or merged.get("storyTimeEnd") or "",
        "recorded_at": str(merged.get("recorded_at") or merged.get("recordedAt") or ""),
        "truth_scope": str(merged.get("truth_scope") or "objective"),
        "knower_ids": knower_ids,
        "actors": actors,
        "location": str(merged.get("location") or ""),
        "action": str(merged.get("action") or merged.get("summary") or ""),
        "outcome": str(merged.get("outcome") or merged.get("result") or ""),
        "objects": objects,
        "threads": _as_list(merged.get("threads") or merged.get("clues")),
        "causes": causes,
        "effects": effects,
        "beliefs_before": _as_mapping(merged.get("beliefs_before") or merged.get("beliefsBefore")),
        "beliefs_after": _as_mapping(merged.get("beliefs_after") or merged.get("beliefsAfter")),
        "state_delta": state_delta,
        "source_document_id": str(merged.get("source_document_id") or source_document_id or ""),
        "source_revision_id": str(merged.get("source_revision_id") or source_revision_id or ""),
        "source_span": dict(source_span or merged.get("source_span") or {}),
        "confidence": round(confidence, 3),
        "superseded_by": merged.get("superseded_by"),
        "invalidated_at_revision": str(merged.get("invalidated_at_revision") or ""),
    }


def build_narrative_event_projection(
    chapter_id: str,
    events: Sequence[Mapping[str, Any]],
    *,
    source_document_id: str = "",
    source_revision_id: str = "",
) -> Dict[str, Any]:
    revision = str(source_revision_id or "").strip() or derive_event_revision_id(chapter_id, events)
    projected = [
        normalise_narrative_event(
            event,
            chapter_id=str(chapter_id),
            index=index,
            source_document_id=source_document_id,
            source_revision_id=revision,
        )
        for index, event in enumerate(events or [])
        if isinstance(event, Mapping)
    ]
    return {
        "schema_version": NARRATIVE_EVENT_SCHEMA_VERSION,
        "chapter_id": str(chapter_id),
        "revision_id": revision,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(projected),
        "events": projected,
    }


def _projection_path(root_dir: Path, chapter_id: str) -> Path:
    return Path(root_dir) / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / _EVENT_FILENAME


def write_narrative_event_projection(
    root_dir: Path,
    chapter_id: str,
    events: Sequence[Mapping[str, Any]],
    *,
    source_document_id: str = "",
    source_revision_id: str = "",
) -> Path:
    projection = build_narrative_event_projection(
        chapter_id,
        events,
        source_document_id=source_document_id,
        source_revision_id=source_revision_id,
    )
    target = _projection_path(root_dir, str(chapter_id))
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    return target


def load_narrative_event_projections(root_dir: Path, chapter_id: Optional[str] = None) -> List[Dict[str, Any]]:
    root = Path(root_dir)
    chapters_root = root / "workspace" / "chapters"
    paths: Iterable[Path]
    if chapter_id is not None:
        paths = [_projection_path(root, str(chapter_id))]
    else:
        paths = chapters_root.glob(f"chapter_*/reports/{_EVENT_FILENAME}")
    result: List[Dict[str, Any]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, Mapping) or payload.get("schema_version") != NARRATIVE_EVENT_SCHEMA_VERSION:
            continue
        result.extend(item for item in payload.get("events", []) if isinstance(item, Mapping))
    return [dict(item) for item in result]


def build_event_evidence_context(
    events: Sequence[Mapping[str, Any]],
    *,
    actor: Optional[str] = None,
    object_name: Optional[str] = None,
    thread: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Return short, source-labelled constraints for a writer/auditor context."""

    def contains(values: Any, needle: Optional[str]) -> bool:
        if not needle:
            return True
        return any(str(needle) in str(value) for value in _as_list(values))

    selected: List[Dict[str, Any]] = []
    for event in events:
        if not contains(event.get("actors"), actor):
            continue
        if not contains(event.get("objects"), object_name):
            continue
        if not contains(event.get("threads"), thread):
            continue
        chapter_id = str(event.get("chapter_id") or "?")
        event_id = str(event.get("id") or "?")
        action = str(event.get("action") or "").strip()
        outcome = str(event.get("outcome") or "").strip()
        summary = action if not outcome else f"{action}；结果：{outcome}"
        selected.append(
            {
                "event_id": event_id,
                "chapter_id": chapter_id,
                "text": f"[硬事实][event:{event_id}][第{chapter_id}章] {summary}".strip(),
                "source_document_id": event.get("source_document_id", ""),
                "source_revision_id": event.get("source_revision_id", ""),
                "source_span": event.get("source_span", {}),
                "confidence": event.get("confidence", 0.0),
            }
        )
    selected.sort(key=lambda item: (_chapter_sort_value(item.get("chapter_id")) or -1), reverse=True)
    return selected[: max(1, int(limit))]


__all__ = [
    "NARRATIVE_EVENT_SCHEMA_VERSION",
    "build_event_evidence_context",
    "build_narrative_event_projection",
    "derive_event_revision_id",
    "load_narrative_event_projections",
    "normalise_narrative_event",
    "write_narrative_event_projection",
]
