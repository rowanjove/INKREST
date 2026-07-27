"""Lightweight project/work snapshots for the pet assistant (山山)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_work_snapshot(root: Path) -> Dict[str, Any]:
    """Current project scale, targets, outline readiness, chapters written."""
    snapshot: Dict[str, Any] = {
        "scale": "",
        "scale_label": "",
        "target_chapters": 0,
        "chapters_written": 0,
        "has_macro_outline": False,
    }
    try:
        outline = _read_json(root / "workspace" / "outline.json")
        meta = _read_json(root / "config" / "project_meta.json")
        sp = outline.get("scale_profile") or meta.get("scale_profile") or {}
        if isinstance(sp, dict):
            snapshot["scale"] = str(sp.get("scale") or meta.get("scale") or "")
            snapshot["scale_label"] = str(sp.get("label") or meta.get("scale_label") or "")
            snapshot["target_chapters"] = int(
                sp.get("target_chapters")
                or outline.get("target_chapters")
                or meta.get("target_chapters")
                or 0
            )
        macro = outline.get("macro_outline") or []
        snapshot["has_macro_outline"] = bool(macro)

        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(root)
        snapshot["chapters_written"] = int(store.count_chapters_indexed())
    except Exception:
        pass
    return snapshot


def _chapter_dir(root: Path, chapter_id: str) -> Optional[Path]:
    cid = str(chapter_id or "").strip()
    if not cid:
        return None
    safe = cid.replace("/", "").replace("\\", "")
    if not safe:
        return None
    return root / "workspace" / "chapters" / f"chapter_{safe}"


def summarize_unified_gate(root: Path, chapter_id: str) -> Optional[str]:
    """One-line unified gate summary for assistant context (≤ ~160 chars)."""
    chapter_dir = _chapter_dir(root, chapter_id)
    if not chapter_dir:
        return None
    doc = _read_json(chapter_dir / "reports" / "unified_gate.json")
    if not doc:
        return None

    if doc.get("overall_pass") is True:
        score = (doc.get("quality") or {}).get("overall_score")
        tail = f"，得分 {score}" if score is not None else ""
        return f"统一门禁：已通过{tail}"

    quality = doc.get("quality") or {}
    audit = doc.get("audit") or {}
    blocked = quality.get("blocked_by") or []
    blocked_txt = "、".join(str(x) for x in blocked[:3]) if blocked else "质量守卫"
    risk = audit.get("risk_level") or "—"
    issues = int(audit.get("issue_count") or 0)
    guard = quality.get("guard_status") or ""
    parts = [f"统一门禁：未通过；拦截项 {blocked_txt}"]
    if guard:
        parts.append(f"守卫 {guard}")
    if issues:
        parts.append(f"审校问题 {issues} 条")
    if risk and risk != "—":
        parts.append(f"风险 {risk}")
    text = "；".join(parts)
    return text[:160]


def enrich_task_summaries(root: Path, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for task in tasks:
        row = dict(task)
        ch = row.get("chapter_id")
        if ch:
            gate = summarize_unified_gate(root, str(ch))
            if gate:
                row["gate_summary"] = gate
        out.append(row)
    return out


def format_repair_steps_hint(chapter_id: str, stage: str = "") -> str:
    """Three-step repair guidance aligned with chapter maintenance UI."""
    stage_part = f"（当前：{stage}）" if stage else ""
    return (
        f"第 {chapter_id} 章{stage_part}建议："
        "1) 正文页改稿 → 2) 生产中心「重跑门禁」 → 3) 通过后在生产中心确认继续生产"
    )


def format_work_snapshot_line(work: Dict[str, Any]) -> str:
    """Human-readable one line for LLM system context."""
    scale = work.get("scale_label") or work.get("scale") or "未设定体量"
    target = int(work.get("target_chapters") or 0)
    written = int(work.get("chapters_written") or 0)
    outline_ok = "已有卷纲" if work.get("has_macro_outline") else "卷纲待完善"
    target_part = f"/{target}" if target > 0 else ""
    return f"{scale}，已写 {written}{target_part} 章，{outline_ok}"


def format_factory_brief(factory: Dict[str, Any]) -> str:
    """Compact factory-console summary for the pet assistant."""
    status = factory.get("factory_status") if isinstance(factory.get("factory_status"), dict) else {}
    brief = factory.get("operator_brief") if isinstance(factory.get("operator_brief"), dict) else {}
    repair = factory.get("repair") if isinstance(factory.get("repair"), dict) else {}
    mode = factory.get("mode_profile") if isinstance(factory.get("mode_profile"), dict) else {}
    state = str(status.get("state") or "unknown")
    completed = int(status.get("completed_chapters") or 0)
    target = int(status.get("target_chapters") or 0)
    blocked = int(repair.get("blocked_count") or 0)
    progress = f"{completed}/{target}" if target else str(completed)
    lines = [
        f"模式 {mode.get('label') or '新手全自动'}",
        f"状态 {state}，进度 {progress} 章",
    ]
    if blocked:
        lines.append(f"阻断 {blocked} 章")
    if brief.get("summary"):
        lines.append(str(brief["summary"]))
    return "；".join(lines)
