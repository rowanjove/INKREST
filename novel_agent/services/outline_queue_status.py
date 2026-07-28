"""Combined outline + arc queue status for UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from novel_agent.services.arc_queue import load_workspace_arcs
from novel_agent.services.outline_sync import check_arc_queue_stale
from novel_agent.services.rolling_planner import (
    _macro_arc_for_chapter,
    count_pending_briefs,
    max_generated_chapter_num,
    _scale_flags,
)


def build_outline_queue_status(
    root_dir: Path,
    *,
    complete_fn: Optional[Callable[[str], bool]] = None,
) -> Dict[str, Any]:
    from novel_agent.services.rolling_planner import _load_outline

    outline = _load_outline(root_dir)
    stale = check_arc_queue_stale(root_dir)
    arcs = load_workspace_arcs(root_dir)
    scale, window, _, target = _scale_flags(root_dir)

    last_written = 0
    pending = 0
    if complete_fn:
        last_written = max_generated_chapter_num(root_dir, complete_fn)
        pending = count_pending_briefs(root_dir, complete_fn)
    else:
        last_written = max_generated_chapter_num(root_dir)

    macro = outline.get("macro_outline") or []
    _, current_macro = _macro_arc_for_chapter(outline, last_written + 1 if last_written else 1)

    brief_ranges = []
    for arc in arcs:
        chs = arc.get("chapters") or []
        ids = [str(c.get("chapter_id") or "") for c in chs if isinstance(c, dict)]
        nums = [int(x) for x in ids if x.isdigit()]
        brief_ranges.append(
            {
                "arc_id": arc.get("arc_id"),
                "arc_name": arc.get("arc_name"),
                "brief_count": len(chs),
                "chapter_min": min(nums) if nums else None,
                "chapter_max": max(nums) if nums else None,
            }
        )

    return {
        "scale": scale,
        "planning_window": window,
        "target_chapters": target,
        "macro_arc_count": len(macro),
        "workspace_arc_count": len(arcs),
        "last_written_chapter": last_written,
        "pending_briefs": pending,
        "current_macro_arc": {
            "arc_id": current_macro.get("arc_id"),
            "name": current_macro.get("name"),
            "chapters": current_macro.get("chapters"),
        },
        "brief_ranges": brief_ranges,
        "arc_queue_stale": stale,
        "outline_layer_impl": outline.get("outline_layer_impl"),
    }