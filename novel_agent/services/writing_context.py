"""Recent chapter context for managing editor / split window."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from novel_agent.services.rolling_planner import format_chapter_id


def _chapter_num(chapter_id: str) -> int:
    raw = str(chapter_id or "").strip()
    return int(raw) if raw.isdigit() else 0


def gather_recent_writing_context(
    root_dir: Path,
    *,
    before_chapter: int,
    max_chapters: int = 3,
    max_chars_per_summary: int = 400,
) -> Dict[str, Any]:
    """Summaries and output_state hints from chapters before `before_chapter`."""
    ws = root_dir / "workspace" / "chapters"
    if not ws.is_dir() or before_chapter <= 1:
        return {"recent_chapters": [], "continuity_hint": ""}

    lookback = max(max_chapters * 3, 12)
    start_num = max(1, before_chapter - lookback)
    arc_states: Dict[str, str] = {}
    for arc_path in (root_dir / "workspace").glob("arc_*.json"):
        try:
            arc = json.loads(arc_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for ch in arc.get("chapters") or []:
            cid = str(ch.get("chapter_id") or "").strip()
            if cid:
                arc_states[cid] = str(ch.get("output_state") or "")

    candidates: List[tuple] = []
    for num in range(before_chapter - 1, start_num - 1, -1):
        cid = format_chapter_id(num) if num < 1000 else str(num)
        d = ws / f"chapter_{cid}"
        if not d.is_dir():
            continue
        final = d / "chapter_final.txt"
        if not final.is_file():
            continue
        try:
            text = final.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if len(text) < 80:
            continue
        summary = ""
        sum_path = d / "chapter_summary.md"
        if sum_path.is_file():
            try:
                summary = sum_path.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        out_state = arc_states.get(cid, "")
        candidates.append((num, cid, summary, out_state, len(text)))

    candidates.sort(key=lambda x: x[0], reverse=True)
    recent: List[Dict[str, Any]] = []
    for num, cid, summary, out_state, wc in candidates[:max_chapters]:
        snippet = summary[:max_chars_per_summary] if summary else f"（已写正文约 {wc} 字，无摘要）"
        recent.append(
            {
                "chapter_id": cid,
                "summary": snippet,
                "output_state": out_state[:200] if out_state else "",
            }
        )

    hint = ""
    if recent:
        last = recent[0]
        hint = (
            f"上一章（{last['chapter_id']}）结束状态：{last.get('output_state') or '见摘要'}。"
            "拆章时请衔接 input_state / output_state 链。"
        )
    return {"recent_chapters": recent, "continuity_hint": hint}


def format_context_for_managing_editor(ctx: Dict[str, Any]) -> str:
    recent = ctx.get("recent_chapters") or []
    if not recent:
        return ""
    lines = ["## 已写章节衔接（拆章必须对齐）"]
    for item in reversed(recent):
        lines.append(
            f"- 第 {item.get('chapter_id')} 章：{item.get('summary', '')[:300]}"
        )
    hint = str(ctx.get("continuity_hint") or "").strip()
    if hint:
        lines.append(hint)
    return "\n".join(lines)