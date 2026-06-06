"""Normalize macro outlines for long / epic / infinite scales."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple

MAX_ARC_SPAN_EPIC = 80
MAX_ARC_SPAN_LONG = 100
MIN_MACRO_ARCS_EPIC = 3


def _parse_chapter_range(raw: Any) -> Tuple[int, int]:
    if isinstance(raw, int):
        return raw, raw
    if not isinstance(raw, str):
        return 1, 1
    text = raw.strip().replace("章", "").replace("第", "")
    m = re.match(r"^(\d+)\s*[-~–—]\s*(\d+)$", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)$", text)
    if m:
        n = int(m.group(1))
        return n, n
    return 1, 1


def _arc_span(arc: Dict[str, Any]) -> int:
    start, end = _parse_chapter_range(arc.get("chapters", "1-1"))
    return max(1, end - start + 1)


def normalize_macro_outline(
    macro_outline: List[Dict[str, Any]],
    *,
    target_chapters: int,
    scale: str,
) -> List[Dict[str, Any]]:
    """Split oversized arc ranges; epic/infinite must not use a single 1-N arc."""
    if not macro_outline:
        return macro_outline

    scale = (scale or "").lower()
    if scale not in ("long", "epic", "infinite"):
        return macro_outline

    max_span = MAX_ARC_SPAN_EPIC if scale in ("epic", "infinite") else MAX_ARC_SPAN_LONG
    target = max(int(target_chapters or 0), max_span)
    expanded: List[Dict[str, Any]] = []

    for arc in macro_outline:
        if not isinstance(arc, dict):
            continue
        start, end = _parse_chapter_range(arc.get("chapters", "1-1"))
        span = end - start + 1
        base_id = str(arc.get("arc_id") or f"A{len(expanded) + 1:02d}")
        if span <= max_span:
            item = copy.deepcopy(arc)
            item["arc_id"] = base_id
            item["chapters"] = f"{start}-{end}"
            expanded.append(item)
            continue
        chunk_idx = 0
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + max_span - 1, end)
            chunk_idx += 1
            suffix = f"_{chunk_idx:02d}" if span > max_span else ""
            item = copy.deepcopy(arc)
            item["arc_id"] = f"{base_id}{suffix}" if suffix else base_id
            item["name"] = f"{arc.get('name', base_id)}（{cursor}-{chunk_end}）"
            item["chapters"] = f"{cursor}-{chunk_end}"
            expanded.append(item)
            cursor = chunk_end + 1

    if scale in ("epic", "infinite") and len(expanded) < MIN_MACRO_ARCS_EPIC and target >= 200:
        # 仅有一个宏观阶段时，按目标章数切为多卷骨架
        if len(expanded) == 1:
            only = expanded[0]
            s, e = _parse_chapter_range(only.get("chapters"))
            total = e - s + 1
            if total > max_span:
                expanded = []
                cursor = s
                part = 0
                while cursor <= e:
                    part += 1
                    ce = min(cursor + max_span - 1, e)
                    item = copy.deepcopy(only)
                    item["arc_id"] = f"{only.get('arc_id', 'A01')}_{part:02d}"
                    item["chapters"] = f"{cursor}-{ce}"
                    expanded.append(item)
                    cursor = ce + 1

    return expanded