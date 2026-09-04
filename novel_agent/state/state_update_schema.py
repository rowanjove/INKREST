"""JSON Schema for LLM state_update payloads."""

from __future__ import annotations

from typing import Any, Dict

_OBJECT_ITEMS = {"type": "array", "items": {"type": "object"}}

STATE_UPDATE_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "events": _OBJECT_ITEMS,
        "objects": _OBJECT_ITEMS,
        "threads": _OBJECT_ITEMS,
        "timeline_nodes": _OBJECT_ITEMS,
        "timeline_edges": _OBJECT_ITEMS,
        "foreshadows": _OBJECT_ITEMS,
        "hooks": _OBJECT_ITEMS,
        "reader_promises": _OBJECT_ITEMS,
        "secrets": _OBJECT_ITEMS,
        "character_relations": _OBJECT_ITEMS,
        "character_memories": _OBJECT_ITEMS,
        "character_behaviors": _OBJECT_ITEMS,
        "characters": {"type": "object"},
    },
}
