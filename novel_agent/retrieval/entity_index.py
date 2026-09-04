"""Resolve character/object/thread names to SQLite row ids."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


def build_entity_alias_map(store: Any) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    characters = store.list_characters() if hasattr(store, "list_characters") else {}
    if isinstance(characters, Mapping):
        for char_id, payload in characters.items():
            row_id = str(char_id)
            mapping[row_id] = row_id
            name = str((payload or {}).get("name") or "").strip()
            if name:
                mapping[name] = row_id
    for item in getattr(store, "list_objects", lambda: [])() or []:
        if not isinstance(item, Mapping):
            continue
        row_id = str(item.get("id") or "").strip()
        if not row_id:
            continue
        mapping[row_id] = row_id
        name = str(item.get("name") or "").strip()
        if name:
            mapping[name] = row_id
    for item in getattr(store, "list_threads", lambda: [])() or []:
        if not isinstance(item, Mapping):
            continue
        row_id = str(item.get("id") or "").strip()
        if not row_id:
            continue
        mapping[row_id] = row_id
        title = str(item.get("title") or "").strip()
        if title:
            mapping[title] = row_id
    return mapping


def expand_entity_tokens(tokens: Iterable[Any], alias_map: Mapping[str, str]) -> List[str]:
    expanded: List[str] = []
    wanted_ids = set()
    for token in tokens:
        text = str(token or "").strip()
        if not text:
            continue
        if text not in expanded:
            expanded.append(text)
        row_id = str(alias_map.get(text) or text)
        wanted_ids.add(row_id)
        if row_id not in expanded:
            expanded.append(row_id)
    for alias, row_id in alias_map.items():
        if row_id in wanted_ids and alias not in expanded:
            expanded.append(alias)
    return expanded


def format_live_character_state(
    characters: Mapping[str, Any],
    scene_tokens: Iterable[Any],
    alias_map: Mapping[str, str],
) -> str:
    wanted = set(expand_entity_tokens(scene_tokens, alias_map))
    lines = []
    for char_id, payload in (characters or {}).items():
        name = str((payload or {}).get("name") or char_id)
        if str(char_id) not in wanted and name not in wanted:
            continue
        location = str((payload or {}).get("location") or "").strip()
        emotion = str((payload or {}).get("emotion") or "").strip()
        bits = [f"id={char_id}", f"name={name}"]
        if location:
            bits.append(f"location={location}")
        if emotion:
            bits.append(f"emotion={emotion}")
        lines.append("- " + " ".join(bits))
    return "\n".join(lines)
