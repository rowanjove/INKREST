from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_TYPES = ("铺垫章", "蓄力章", "爆发章", "过渡章")

TYPE_TO_SCENE = {
    "铺垫章": ("setup", "brief"),
    "蓄力章": ("build", "normal"),
    "爆发章": ("burst", "full"),
    "过渡章": ("transition", "skip"),
}

VALID_SCENE_TYPES = {"setup", "build", "burst", "transition"}
VALID_DETAIL_LEVELS = {"skip", "brief", "normal", "full"}
VALID_HOOK_TYPES = {"info", "action", "reversal"}


def normalize_chapter_window(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize AI chapter-plan rows into structured rolling-window items."""
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        goal = item.get("goal") or item.get("chapter_goal") or item.get("title") or item.get("chapter_title") or ""
        chapter_type = item.get("chapter_type") or ("爆发章" if (index + 1) % 5 == 0 else "铺垫章")
        if chapter_type not in DEFAULT_TYPES:
            chapter_type = "铺垫章"
        default_scene_type, default_detail_level = TYPE_TO_SCENE[chapter_type]
        scene_type = item.get("scene_type") or default_scene_type
        if scene_type not in VALID_SCENE_TYPES:
            scene_type = default_scene_type
        detail_level = item.get("detail_level") or default_detail_level
        if detail_level not in VALID_DETAIL_LEVELS:
            detail_level = default_detail_level
        hook_type = item.get("hook_type") or ("action" if chapter_type in ("爆发章", "过渡章") else "info")
        if hook_type not in VALID_HOOK_TYPES:
            hook_type = "info"
        normalized.append({
            "chapter_id": item.get("chapter_id", f"{index + 1:03d}"),
            "title": item.get("title") or item.get("chapter_title") or "",
            "goal": goal,
            "chapter_type": chapter_type,
            "scene_type": scene_type,
            "detail_level": detail_level,
            "plot_task": item.get("plot_task") or {
                "what_happens": goal,
                "result": item.get("output_state", ""),
            },
            "character_task": item.get("character_task") or {
                "focus": item.get("focus_characters", []),
                "change": item.get("character_change", ""),
            },
            "payoff_task": item.get("payoff_task") or {
                "has_payoff": chapter_type == "爆发章",
                "type": item.get("reader_payoff", ""),
                "setup": "",
            },
            "hook": item.get("hook", ""),
            "hook_type": hook_type,
            "foreshadow": item.get("foreshadow") or {
                "plant": item.get("foreshadow_plant", []),
                "reveal": item.get("foreshadow_reveal", []),
            },
            "input_state": item.get("input_state", ""),
            "output_state": item.get("output_state", ""),
            "must_include": item.get("must_include", []),
            "must_not_include": item.get("must_not_include", []),
        })
    return normalized


def build_pacing_report(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check simple longform pacing ratios for a rolling chapter window."""
    window = items[:10]
    setup_count = sum(1 for item in window if item.get("chapter_type") == "铺垫章")
    build_count = sum(1 for item in window if item.get("chapter_type") == "蓄力章")
    burst_count = sum(1 for item in window if item.get("chapter_type") == "爆发章")
    transition_count = sum(1 for item in window if item.get("chapter_type") == "过渡章")

    issues: List[str] = []
    if setup_count > 3:
        issues.append("铺垫章过多：每 10 章建议不超过 3 章")
    if build_count > 4:
        issues.append("连续蓄力/铺垫压力过高：每 10 章蓄力章建议不超过 4 章")
    if burst_count < 2 and len(window) >= 10:
        issues.append("爆发章不足：每 10 章建议至少 2 章")

    return {
        "pass": not issues,
        "issues": issues,
        "counts": {
            "setup": setup_count,
            "build": build_count,
            "burst": burst_count,
            "transition": transition_count,
        },
        "window_size": len(window),
    }
