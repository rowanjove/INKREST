"""Hierarchical Context Assembly (L0 Blueprint -> L1 Arc Summary -> L2 Recent Slices).

Inspired by StoryDaemon & Ex3 recursive summarization architectures:
Prevents context window dilution and character drift in 100~2000+ chapter novels
by dynamically compiling a multi-level narrative blueprint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _arc_chapter_span(arc: dict[str, Any]) -> tuple[int, int]:
    """Read arc bounds from start/end fields or a `chapters` range such as '1-5'."""
    start = arc.get("start_chapter")
    end = arc.get("end_chapter")
    try:
        if start is not None and end is not None:
            return int(start), int(end)
    except (TypeError, ValueError):
        pass
    raw = str(arc.get("chapters") or arc.get("chapter_range") or "")
    digits = [int(value) for value in re.findall(r"\d+", raw)]
    if len(digits) >= 2:
        return digits[0], digits[1]
    if len(digits) == 1:
        return digits[0], digits[0]
    return 1, 9999


def _sqlite_chapter_summaries(root: Path) -> dict[str, str]:
    db_path = root / "data" / "novel.sqlite"
    if not db_path.is_file():
        return {}
    try:
        from novel_agent.state.sqlite_schema import safe_connection

        with safe_connection(db_path) as conn:
            rows = conn.execute("select chapter_id, summary from chapter_summaries").fetchall()
        result: dict[str, str] = {}
        for chapter_id, summary in rows:
            text = str(summary or "").strip()
            if not text:
                continue
            key = str(chapter_id)
            result[key] = text
            digits = re.findall(r"\d+", key)
            if digits:
                result[str(int(digits[0]))] = text
                result[f"{int(digits[0]):03d}"] = text
        return result
    except Exception:
        return {}


def _lookup_summary(summaries: dict[str, str], chapter_key: str) -> str:
    if chapter_key in summaries:
        return summaries[chapter_key]
    digits = re.findall(r"\d+", str(chapter_key or ""))
    if not digits:
        return ""
    number = int(digits[0])
    return summaries.get(str(number)) or summaries.get(f"{number:03d}") or ""


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def assemble_hierarchical_context(
    root_dir: Path,
    target_chapter_id: str,
    *,
    max_chars: int = 4000,
) -> dict[str, Any]:
    """Assemble L0 (Macro) + L1 (Arc) + L2 (Recent chapters & Fact slices)."""
    root = Path(root_dir)
    outline_data = _safe_read_json(root / "workspace" / "outline.json")
    if not outline_data:
        outline_data = _safe_read_json(root / "outline.json")

    # ---- Level 0: Macro Blueprint ----
    title = str(outline_data.get("chosen_title") or outline_data.get("title") or "未命名作品")
    theme = str(outline_data.get("core_theme") or outline_data.get("theme") or "")
    genre = str(outline_data.get("genre") or outline_data.get("genre_genes") or "")
    worldview = str(outline_data.get("worldview") or outline_data.get("background") or "")
    target_ch = outline_data.get("target_chapters") or 0

    l0_parts = [f"《{title}》"]
    if genre:
        l0_parts.append(f"题材基因: {genre}")
    if target_ch:
        l0_parts.append(f"目标总章数: {target_ch}章")
    if theme:
        l0_parts.append(f"核心爽点与主线: {theme[:200]}")
    if worldview:
        l0_parts.append(f"世界观底层铁律: {worldview[:300]}")
    level0_text = "\n".join(l0_parts)

    # ---- Level 1: Arc Summary ----
    macro_outline = outline_data.get("macro_outline") or []
    macro_outline = macro_outline if isinstance(macro_outline, list) else []

    digits = re.findall(r"\d+", str(target_chapter_id or ""))
    ch_num = int(digits[0]) if digits else 1

    current_arc_info: dict[str, Any] = {}
    completed_arcs: list[dict[str, Any]] = []

    for arc in macro_outline:
        if not isinstance(arc, dict):
            continue
        start_ch, end_ch = _arc_chapter_span(arc)
        if start_ch <= ch_num <= end_ch:
            current_arc_info = arc
        elif end_ch < ch_num:
            completed_arcs.append(arc)

    l1_parts = []
    if completed_arcs:
        past_summaries = []
        for arc in completed_arcs[-3:]:
            name = arc.get("arc_name") or arc.get("title") or f"第{arc.get('arc_id', '')}卷"
            goal = arc.get("goal") or arc.get("summary") or ""
            past_summaries.append(f"• {name}（已完结）: {goal[:100]}")
        l1_parts.append("前序分卷里程碑:\n" + "\n".join(past_summaries))

    sqlite_summaries = _sqlite_chapter_summaries(root)

    if current_arc_info:
        curr_name = (
            current_arc_info.get("arc_name")
            or current_arc_info.get("title")
            or "当前卷"
        )
        curr_goal = current_arc_info.get("goal") or current_arc_info.get("arc_goal") or ""
        curr_tp = current_arc_info.get("turning_point") or ""
        l1_parts.append(f"当前所在卷: {curr_name}")
        if curr_goal:
            l1_parts.append(f"• 本卷核心任务: {curr_goal}")
        else:
            start_ch, end_ch = _arc_chapter_span(current_arc_info)
            rolled = []
            for number in range(start_ch, min(end_ch, ch_num - 1) + 1):
                text = _lookup_summary(sqlite_summaries, str(number))
                if text:
                    rolled.append(text[:80])
            if rolled:
                l1_parts.append("• 本卷已发生: " + "；".join(rolled[-5:]))
        if curr_tp:
            l1_parts.append(f"• 本卷关键转折点: {curr_tp}")
    else:
        l1_parts.append("当前所在卷: 正篇连载推进中")

    level1_text = "\n".join(l1_parts)

    # ---- Level 2: Recent Chapter Summaries & Fact Slices ----
    chapters_dir = root / "workspace" / "chapters"
    recent_slices = []

    # Look back up to 3 preceding chapters (disk first, SQLite if missing)
    for offset in range(3, 0, -1):
        prev_num = ch_num - offset
        if prev_num < 1:
            continue
        prev_id = f"{prev_num:03d}"
        ch_path = chapters_dir / f"chapter_{prev_id}"
        if not ch_path.is_dir():
            ch_path = chapters_dir / f"chapter_{prev_num}"
        summary_data = _safe_read_json(ch_path / "summary.json") if ch_path.is_dir() else {}
        plan_data = _safe_read_json(ch_path / "plan.json") if ch_path.is_dir() else {}
        title_text = str(plan_data.get("chapter_title") or f"第{prev_num}章")
        brief = str(
            summary_data.get("summary")
            or summary_data.get("brief")
            or plan_data.get("goal")
            or ""
        ).strip()
        if not brief or brief == "本章已完成":
            brief = _lookup_summary(sqlite_summaries, prev_id) or brief
        if not brief:
            continue
        recent_slices.append({
            "chapter_id": prev_id,
            "title": title_text,
            "summary": brief[:250],
        })

    l2_parts = []
    if recent_slices:
        for item in recent_slices:
            l2_parts.append(f"• 第{item['chapter_id']}章《{item['title']}》: {item['summary']}")
    else:
        l2_parts.append("• 本书序幕或首卷开篇，无前序章节历史。")

    level2_text = "\n".join(l2_parts)

    # Compile Final Prompt Block
    block = (
        f"### 【全书宏观蓝图 (L0)】\n{level0_text}\n\n"
        f"### 【分卷节奏目标 (L1)】\n{level1_text}\n\n"
        f"### 【前情精细切片 (L2)】\n{level2_text}"
    )

    if len(block) > max_chars:
        block = block[:max_chars - 3] + "..."

    return {
        "level0_blueprint": level0_text,
        "level1_arc_summary": level1_text,
        "level2_recent_chapters": recent_slices,
        "compiled_prompt_block": block,
        "total_chars": len(block),
        "estimated_tokens": int(len(block) * 0.75),
    }
