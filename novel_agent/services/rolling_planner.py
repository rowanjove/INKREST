"""Rolling chapter queue: initial arcs, replenish planning window, episode arcs."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from novel_agent.control.outline_structure import _parse_chapter_range, normalize_macro_outline
from novel_agent.control.scale_profile import load_outline_scale_profile
from novel_agent.logging_config import get_logger
from novel_agent.services.arc_queue import (
    chapter_id_from_brief,
    load_workspace_arcs,
    sort_briefs_by_dependencies,
)

logger = get_logger("services.rolling_planner")

DEFAULT_REPLENISH_BUFFER = 15


def format_chapter_id(num: int) -> str:
    if num < 1000:
        return f"{num:03d}"
    return str(num)


def _load_outline(root_dir: Path) -> Dict[str, Any]:
    for rel in ("workspace/outline.json", "outline.json"):
        path = root_dir / rel
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _write_arc(root_dir: Path, arc: Dict[str, Any]) -> Path:
    aid = str(arc.get("arc_id") or "A01")
    path = root_dir / "workspace" / f"arc_{aid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(arc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _merge_arc_chapters(existing: Dict[str, Any], new_chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for ch in existing.get("chapters") or []:
        cid = chapter_id_from_brief(ch)
        if cid:
            by_id[cid] = ch
    for ch in new_chapters:
        cid = chapter_id_from_brief(ch)
        if not cid:
            continue
        if cid in by_id:
            # 勿用补窗结果覆盖未写完章节的标题/目标，避免连写时章名反复变化
            continue
        by_id[cid] = ch
    merged = sort_briefs_by_dependencies(list(by_id.values()))
    out = dict(existing)
    out["chapters"] = merged
    return out


def max_generated_chapter_num(root_dir: Path, complete_fn: Optional[Callable[[str], bool]] = None) -> int:
    """Highest numeric chapter id that counts as generated (or any brief id in arcs)."""
    from novel_agent.services.chapter_highwater import resolve_max_generated_chapter_num

    return resolve_max_generated_chapter_num(root_dir, complete_fn)


def count_pending_briefs(
    root_dir: Path,
    complete_fn: Callable[[str], bool],
) -> int:
    total = 0
    for arc in load_workspace_arcs(root_dir):
        for ch in arc.get("chapters") or []:
            cid = chapter_id_from_brief(ch)
            if cid and not complete_fn(cid):
                total += 1
    return total


def _macro_arc_for_chapter(outline: Dict[str, Any], chapter_num: int) -> Tuple[int, Dict[str, Any]]:
    arcs = outline.get("macro_outline") or []
    for idx, arc in enumerate(arcs):
        if not isinstance(arc, dict):
            continue
        start, end = _parse_chapter_range(arc.get("chapters", "1-1"))
        if start <= chapter_num <= end:
            return idx, arc
    if arcs and isinstance(arcs[-1], dict):
        return len(arcs) - 1, arcs[-1]
    return 0, {"arc_id": "A01", "goal": outline.get("core_theme", ""), "chapters": "1-999"}


def _episode_arc_id(episode_index: int) -> str:
    return f"EP{episode_index:02d}"


def _scale_flags(root_dir: Path) -> Tuple[str, int, int, int]:
    outline = _load_outline(root_dir)
    profile = outline.get("scale_profile") or load_outline_scale_profile(root_dir) or {}
    scale = str(profile.get("scale") or "medium")
    window = int(profile.get("planning_window") or 20)
    ep_range = profile.get("episode_chapters") or [20, 50]
    if isinstance(ep_range, list) and ep_range:
        episode_size = int(ep_range[0])
    else:
        episode_size = 20
    target = int(outline.get("target_chapters") or profile.get("target_chapters") or profile.get("max_chapters") or 999999)
    return scale, window, episode_size, target


def split_window_briefs(
    root_dir: Path,
    *,
    start_chapter: int,
    count: int,
    instructions: str = "",
    macro_arc_index: int = 0,
    writing_context: str = "",
) -> Dict[str, Any]:
    from novel_agent.agents.managing_editor import ManagingEditorAgent
    from novel_agent.control.chapter_window import normalize_chapter_window
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.prompts import PromptRepository

    outline = _load_outline(root_dir)
    if not outline:
        raise ValueError("No outline found")

    end = start_chapter + count - 1
    plan_outline = copy.deepcopy(outline)
    arcs = plan_outline.get("macro_outline") or [{}]
    idx = min(macro_arc_index, max(0, len(arcs) - 1))
    arc = dict(arcs[idx]) if isinstance(arcs[idx], dict) else {"goal": str(arcs[idx])}
    arc["chapters"] = f"{start_chapter}-{end}"
    if instructions:
        arc["goal"] = f"{arc.get('goal', '')}\n补充：{instructions}".strip()
    plan_outline["macro_outline"] = [arc]

    config = PipelineConfig.from_config(root_dir)
    editor = ManagingEditorAgent(config.get_llm("managing_editor"), PromptRepository(root_dir))
    result = editor.split_chapters(plan_outline, arc_index=0, writing_context=writing_context)
    chapters = []
    for i, ch in enumerate((result.get("chapters") or [])[:count]):
        n = start_chapter + i
        chapters.append({
            **ch,
            "chapter_id": format_chapter_id(n),
            "chapter_title": ch.get("chapter_title") or ch.get("title") or f"第 {n} 章",
            "chapter_goal": ch.get("chapter_goal") or ch.get("goal") or arc.get("goal", "推进主线"),
        })
    result["chapters"] = normalize_chapter_window(chapters)
    result.setdefault("arc_id", arc.get("arc_id", f"A{macro_arc_index + 1:02d}"))
    return result


def append_briefs_to_queue(root_dir: Path, arc_payload: Dict[str, Any]) -> str:
    scale, _, episode_size, _ = _scale_flags(root_dir)
    chapters = arc_payload.get("chapters") or []
    if not chapters:
        return ""

    first_num = int(chapter_id_from_brief(chapters[0]) or "1")
    arc_id = str(arc_payload.get("arc_id") or "")

    if scale == "infinite":
        ep_index = max(1, (first_num - 1) // max(1, episode_size) + 1)
        arc_id = _episode_arc_id(ep_index)
    elif not arc_id:
        outline = _load_outline(root_dir)
        _, macro = _macro_arc_for_chapter(outline, first_num)
        arc_id = str(macro.get("arc_id") or "A01")

    arc_id = arc_id.replace(" ", "_")
    existing_arcs = {str(a.get("arc_id")): a for a in load_workspace_arcs(root_dir)}
    if arc_id in existing_arcs:
        merged = _merge_arc_chapters(existing_arcs[arc_id], chapters)
        _write_arc(root_dir, merged)
    else:
        payload = {
            "arc_id": arc_id,
            "arc_name": arc_payload.get("arc_name") or arc_payload.get("name") or arc_id,
            "arc_goal": arc_payload.get("arc_goal") or arc_payload.get("goal") or "",
            "chapters": sort_briefs_by_dependencies(chapters),
        }
        _write_arc(root_dir, payload)
    logger.info("Appended %d briefs to arc %s", len(chapters), arc_id)
    return arc_id


async def _raise_if_cancelled(cancel_check: Optional[Callable[[], Any]]) -> None:
    if not cancel_check:
        return
    result = cancel_check()
    if hasattr(result, "__await__"):
        result = await result
    if result:
        raise InterruptedError("客户端已取消同步卷队列")


async def ensure_initial_arcs(
    orchestrator: Any,
    *,
    max_macro_arcs: int = 2,
    cancel_check: Optional[Callable[[], Any]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> int:
    """Create arc_*.json from macro outline when queue is empty (long-form safe: first volumes only)."""
    root = orchestrator.root_dir
    if load_workspace_arcs(root):
        return 0

    outline = _load_outline(root)
    macro = outline.get("macro_outline") or []
    if not macro:
        raise ValueError("大纲缺少 macro_outline，请先生成或保存大纲。")

    profile = outline.get("scale_profile") or {}
    scale = str(profile.get("scale") or "")
    target = int(outline.get("target_chapters") or 20)
    macro = normalize_macro_outline(macro, target_chapters=target, scale=scale)
    outline["macro_outline"] = macro

    written = 0
    limit = len(macro) if scale in ("short", "medium", "micro") else min(max_macro_arcs, len(macro))
    for i in range(limit):
        await _raise_if_cancelled(cancel_check)
        if status_callback:
            status_callback(f"主编拆卷 {i + 1}/{limit}…")
        if hasattr(orchestrator.managing_editor, "asplit_chapters"):
            arc_result = await orchestrator.managing_editor.asplit_chapters(outline, arc_index=i)
        else:
            arc_result = orchestrator.managing_editor.split_chapters(outline, arc_index=i)
        arc_result.setdefault("arc_id", macro[i].get("arc_id", f"A{i + 1:02d}"))
        _write_arc(root, arc_result)
        written += 1
    return written


async def replenish_rolling_window(
    orchestrator: Any,
    *,
    min_buffer: int = DEFAULT_REPLENISH_BUFFER,
    complete_fn: Optional[Callable[[str], bool]] = None,
) -> int:
    """Append next planning_window briefs when pending queue is low."""
    root = orchestrator.root_dir
    complete_fn = complete_fn or orchestrator._chapter_pipeline_complete
    pending = count_pending_briefs(root, complete_fn)
    if pending >= min_buffer:
        return 0

    scale, window, _, target = _scale_flags(root)
    if scale in ("micro", "short") and pending > 0:
        return 0

    last = max_generated_chapter_num(root, complete_fn)
    start = last + 1
    if target < 999999 and start > target:
        return 0

    need = max(window, min_buffer - pending)
    outline = _load_outline(root)
    _, macro = _macro_arc_for_chapter(outline, start)
    macro_index = 0
    for i, a in enumerate(outline.get("macro_outline") or []):
        if isinstance(a, dict) and str(a.get("arc_id")) == str(macro.get("arc_id")):
            macro_index = i
            break

    payload = split_window_briefs(
        root,
        start_chapter=start,
        count=need,
        macro_arc_index=macro_index,
    )
    append_briefs_to_queue(root, payload)
    return len(payload.get("chapters") or [])


async def maybe_open_next_episode(orchestrator: Any, *, complete_fn: Optional[Callable[[str], bool]] = None) -> bool:
    """infinite / container_episode: queue next episode arc when current EP* is exhausted."""
    root = orchestrator.root_dir
    scale, _, episode_size, target = _scale_flags(root)
    if scale != "infinite":
        return False

    complete_fn = complete_fn or orchestrator._chapter_pipeline_complete
    if count_pending_briefs(root, complete_fn) > 0:
        return False

    last = max_generated_chapter_num(root, complete_fn)
    start = last + 1
    if target < 999999 and start > target:
        return False

    payload = split_window_briefs(root, start_chapter=start, count=episode_size, macro_arc_index=0)
    payload["arc_id"] = _episode_arc_id(max(1, (start - 1) // max(1, episode_size) + 1))
    payload["arc_name"] = f"单元 {(start - 1) // max(1, episode_size) + 1}"
    append_briefs_to_queue(root, payload)
    return True


async def prepare_queue_for_run(
    orchestrator: Any,
    *,
    cancel_check: Optional[Callable[[], Any]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Ensure arcs exist and replenish before batch run."""
    await _raise_if_cancelled(cancel_check)
    if status_callback:
        status_callback("检查卷队列…")
    created = await ensure_initial_arcs(
        orchestrator,
        cancel_check=cancel_check,
        status_callback=status_callback,
    )
    await _raise_if_cancelled(cancel_check)
    if status_callback and created:
        status_callback(f"已创建 {created} 个卷文件")
    if status_callback:
        status_callback("补全规划窗口…")
    added = await replenish_rolling_window(orchestrator)
    await _raise_if_cancelled(cancel_check)
    await maybe_open_next_episode(orchestrator)
    pending = count_pending_briefs(orchestrator.root_dir, orchestrator._chapter_pipeline_complete)
    return {"arcs_created": created, "briefs_added": added, "pending_briefs": pending}