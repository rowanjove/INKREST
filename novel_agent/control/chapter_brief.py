"""Chapter brief expand skip — reuse expanded_plan when goal already rich."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple


def brief_fingerprint(brief: Dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "chapter_id": brief.get("chapter_id"),
            "chapter_goal": brief.get("chapter_goal") or brief.get("goal"),
            "detailed_synopsis": brief.get("detailed_synopsis"),
            "chapter_title": brief.get("chapter_title") or brief.get("title"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def expanded_plan_fingerprint(expanded: Dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "detailed_synopsis": expanded.get("detailed_synopsis"),
            "chapter_goal": expanded.get("chapter_goal"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def should_skip_chapter_planner_expand(
    root_dir: Path,
    chapter_id: str,
    brief: Dict[str, Any],
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Skip chapter_planner LLM when brief already has detailed_synopsis and
    expanded_plan.json matches the same brief fingerprint.
    """
    synopsis = str(brief.get("detailed_synopsis") or "").strip()
    goal = str(brief.get("chapter_goal") or brief.get("goal") or "").strip()
    rich_goal = len(synopsis) >= 40 or len(goal) >= 80
    if not rich_goal:
        return False, "brief_not_rich", {}

    chapter_dir = root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    plan_path = chapter_dir / "expanded_plan.json"
    if not plan_path.is_file():
        return False, "no_expanded_plan", {}

    try:
        expanded = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "expanded_plan_invalid", {}

    if not isinstance(expanded, dict):
        return False, "expanded_plan_invalid", {}

    meta_path = chapter_dir / "expanded_plan.meta.json"
    brief_fp = brief_fingerprint(brief)
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("brief_fp") == brief_fp:
                return True, "cached_expand", expanded
        except Exception:
            pass

    if synopsis and str(expanded.get("detailed_synopsis") or "").strip() == synopsis:
        return True, "synopsis_match", expanded

    return False, "expand_required", {}