"""Compress chapter plan + scene into a short pre-write task card."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

MAX_CARD_CHARS = 900
_BEAT_ORDER = ("开场", "冲突", "转折", "兑现", "钩子")


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Iterable):
        items: List[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text not in items:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def _unique(items: Iterable[str], limit: int = 6) -> List[str]:
    seen: List[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def build_writer_task_card(
    plan: Optional[Mapping[str, Any]] = None,
    scene: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    plan = plan or {}
    scene = scene or {}
    handoff = plan.get("handoff_to_scene_planner") if isinstance(plan.get("handoff_to_scene_planner"), dict) else {}
    must_include = _unique(
        [
            *(_as_list(scene.get("must_include"))),
            *(_as_list(handoff.get("must_include"))),
        ]
    )
    must_not = _unique(
        [
            *(_as_list(scene.get("must_not_include"))),
            *(_as_list(handoff.get("must_not_include"))),
        ]
    )
    beats: List[str] = []
    raw_beats = plan.get("beats") if isinstance(plan.get("beats"), list) else []
    ranked = sorted(
        [item for item in raw_beats if isinstance(item, dict)],
        key=lambda item: _BEAT_ORDER.index(str(item.get("function") or ""))
        if str(item.get("function") or "") in _BEAT_ORDER
        else 99,
    )
    for item in ranked[:3]:
        function = str(item.get("function") or "").strip()
        content = str(item.get("content") or "").strip()
        if content:
            beats.append(f"{function}：{content}" if function else content)

    foreshadow: List[str] = []
    for item in plan.get("foreshadow_plan") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        action = str(item.get("action") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if not title:
            continue
        if action in {"progress", "resolve", "collect"}:
            foreshadow.append(f"{title}（{action}）{('：' + detail) if detail else ''}".strip())
        elif detail:
            foreshadow.append(f"{title}：{detail}")
        else:
            foreshadow.append(title)

    goal = str(
        scene.get("purpose")
        or plan.get("detailed_synopsis")
        or plan.get("chapter_goal")
        or plan.get("chapter_title")
        or ""
    ).strip()
    exit_hook = str(scene.get("exit") or plan.get("exit") or "").strip()
    if not exit_hook:
        for item in reversed(ranked):
            if str(item.get("function") or "") == "钩子":
                exit_hook = str(item.get("content") or "").strip()
                break

    return {
        "goal": goal,
        "must_include": must_include,
        "must_not_include": must_not,
        "beats": beats,
        "foreshadow_collect": _unique(foreshadow, limit=4),
        "exit_hook": exit_hook,
    }


def format_writer_task_card(card: Mapping[str, Any], *, max_chars: int = MAX_CARD_CHARS) -> str:
    if not card:
        return ""
    lines = ["【写前任务卡】"]
    goal = str(card.get("goal") or "").strip()
    if goal:
        lines.append(f"目标：{goal}")
    must_include = _as_list(card.get("must_include"))
    if must_include:
        lines.append("必写：")
        lines.extend(f"- {item}" for item in must_include)
    must_not = _as_list(card.get("must_not_include"))
    if must_not:
        lines.append("禁写：")
        lines.extend(f"- {item}" for item in must_not)
    beats = _as_list(card.get("beats"))
    if beats:
        lines.append("节拍：")
        lines.extend(f"- {item}" for item in beats)
    foreshadow = _as_list(card.get("foreshadow_collect"))
    if foreshadow:
        lines.append("回收/推进伏笔：")
        lines.extend(f"- {item}" for item in foreshadow)
    exit_hook = str(card.get("exit_hook") or "").strip()
    if exit_hook:
        lines.append(f"出口钩子：{exit_hook}")
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text
