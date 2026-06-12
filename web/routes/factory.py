"""Product-level AI factory dashboard summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import APIRouter
from pydantic import BaseModel

import web.context as ws_server

router = APIRouter()


FactoryMode = Literal[
    "newbie_auto",
    "author_copilot",
    "platform_review",
    "longform_stable",
    "studio",
]


class FactoryModeRequest(BaseModel):
    mode: FactoryMode


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _project_name(project_id: str | None, root: Path, outline: Dict[str, Any]) -> str:
    if outline.get("chosen_title"):
        return str(outline["chosen_title"])
    if outline.get("title_options"):
        options = outline.get("title_options")
        if isinstance(options, list) and options:
            return str(options[0])
    if project_id:
        try:
            registry = ws_server.project_manager._read_registry()
            info = registry.get("projects", {}).get(project_id, {})
            if info.get("name"):
                return str(info["name"])
        except Exception:
            pass
        return project_id
    return root.name


def _load_project_meta(root: Path) -> Dict[str, Any]:
    return _read_json(root / "config" / "project_meta.json")


def _write_project_meta(root: Path, meta: Dict[str, Any]) -> None:
    meta_path = root / "config" / "project_meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _infer_mode(meta: Dict[str, Any]) -> str:
    mode = str(meta.get("factory_mode") or meta.get("mode") or "").strip()
    allowed = {
        "newbie_auto",
        "author_copilot",
        "platform_review",
        "longform_stable",
        "studio",
    }
    return mode if mode in allowed else "newbie_auto"


def _planned_chapter_count(outline: Dict[str, Any], root: Path) -> int:
    chapters = outline.get("chapters")
    if isinstance(chapters, list):
        return len(chapters)
    total = 0
    arcs_root = root / "workspace"
    for arc_path in arcs_root.glob("arc_*.json") if arcs_root.is_dir() else []:
        arc = _read_json(arc_path)
        arc_chapters = arc.get("chapters")
        if isinstance(arc_chapters, list):
            total += len(arc_chapters)
    return total


def _target_chapters(outline: Dict[str, Any], meta: Dict[str, Any]) -> int:
    for source in (outline, meta):
        value = source.get("target_chapters")
        if isinstance(value, int) and value > 0:
            return value
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            pass
    scale_profile = outline.get("scale_profile") or meta.get("scale_profile") or {}
    try:
        parsed = int(scale_profile.get("target_chapters") or scale_profile.get("max_chapters") or 0)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError, AttributeError):
        pass
    return 0


def _selling_points(outline: Dict[str, Any]) -> List[str]:
    for key in ("selling_points", "reader_promise", "cool_points"):
        value = outline.get(key)
        if isinstance(value, list):
            return [str(item) for item in value[:5] if str(item).strip()]
    summary = outline.get("summary_card")
    if isinstance(summary, dict):
        promises = summary.get("reader_promise")
        if isinstance(promises, list):
            return [str(item) for item in promises[:5] if str(item).strip()]
        logline = summary.get("logline")
        if logline:
            return [str(logline)]
    return []


def _count_completed_chapters(root: Path) -> int:
    chapters_root = root / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return 0
    completed = 0
    for final_path in chapters_root.glob("chapter_*/chapter_final.txt"):
        try:
            if len(final_path.read_text(encoding="utf-8").strip()) > 50:
                completed += 1
        except OSError:
            continue
    return completed


def _running_task_count() -> int:
    try:
        tasks = ws_server._get_task_manager().list_tasks()
    except Exception:
        return 0
    return len([task for task in tasks if task.get("status") in ("pending", "running")])


def _readiness(outline: Dict[str, Any], root: Path, planned: int) -> Dict[str, Any]:
    checks = [
        ("大纲", bool(outline)),
        ("书名", bool(outline.get("chosen_title") or outline.get("title_options"))),
        ("生产计划", planned > 0),
        ("角色卡", (root / "assets" / "character_cards.yaml").is_file()),
        ("世界观", (root / "assets" / "world_bible.md").is_file()),
        ("风格指南", (root / "assets" / "style_guide.md").is_file()),
    ]
    missing = [label for label, ok in checks if not ok]
    return {"ok": len(checks) - len(missing), "total": len(checks), "missing": missing}


def _exports(root: Path, completed: int) -> Dict[str, bool]:
    has_text = completed > 0
    return {
        "txt_available": has_text,
        "epub_available": has_text,
        "pdf_available": False,
    }


def _alert_title(root: Path, chapter_id: str) -> str:
    plan = _read_json(root / "workspace" / "chapters" / f"chapter_{chapter_id}" / "plan.json")
    return str(plan.get("chapter_title") or plan.get("title") or f"第 {chapter_id} 章")


def _manual_hint(alert: Dict[str, Any]) -> str:
    quality = alert.get("quality") if isinstance(alert.get("quality"), dict) else {}
    blocked_by = quality.get("blocked_by") if isinstance(quality.get("blocked_by"), list) else []
    stage = str(alert.get("last_stage") or "")
    if "ai_flavor" in blocked_by or "style" in blocked_by:
        return "重点改写机器味明显的段落，减少抽象抒情、重复句式和总结式表达，改完后只重跑门禁。"
    if "continuity" in blocked_by:
        return "优先检查人物状态、地点、道具和上一章摘要是否冲突，改完后只重跑门禁。"
    if stage == "batch_retry":
        return "这是批量运行跳过的章节，请先重试本章；若再次失败，再打开章节详情查看任务日志。"
    if stage == "external_review_pending":
        return "该章等待外部平台试审结果，请试发后标记外审通过或回到正文改稿。"
    return "请打开章节详情，优先检查门禁报告中标红的问题段落，修改后只重跑门禁。"


def _recommended_action(alert: Dict[str, Any]) -> str:
    stage = str(alert.get("last_stage") or "")
    if stage == "quality_blocked":
        return "auto_repair"
    if stage == "approval_rejected":
        return "rerun_gate"
    return "manual_edit"


def _repair_summary(root: Path) -> Dict[str, Any]:
    try:
        from novel_agent.services.pipeline_pending import collect_pipeline_alerts_cached

        alerts = collect_pipeline_alerts_cached(root)
    except Exception:
        alerts = []
    items: List[Dict[str, Any]] = []
    for alert in alerts[:10]:
        chapter_id = str(alert.get("chapter_id") or "")
        if not chapter_id:
            continue
        items.append(
            {
                "chapter_id": chapter_id,
                "title": _alert_title(root, chapter_id),
                "reason": str(alert.get("message") or alert.get("last_stage") or "待处理"),
                "recommended_action": _recommended_action(alert),
                "manual_hint": _manual_hint(alert),
                "last_stage": str(alert.get("last_stage") or ""),
                "source": str(alert.get("source") or ""),
            }
        )
    return {"blocked_count": len(alerts), "items": items}


def _pipeline(state: str) -> List[Dict[str, str]]:
    steps = [
        ("planning", "策划"),
        ("writing", "写作"),
        ("polish", "润色"),
        ("audit", "审校"),
        ("repair", "修复"),
        ("archive", "入库"),
    ]
    active_by_state = {
        "empty": "planning",
        "planning": "planning",
        "ready": "planning",
        "running": "writing",
        "blocked": "repair",
        "complete": "archive",
    }
    active = active_by_state.get(state, "planning")
    result: List[Dict[str, str]] = []
    seen_active = False
    for step_id, label in steps:
        if step_id == active:
            seen_active = True
            step_state = "blocked" if state == "blocked" else "active"
        elif not seen_active and state not in ("empty", "planning", "ready"):
            step_state = "done"
        else:
            step_state = "idle"
        result.append({"id": step_id, "label": label, "state": step_state})
    return result


def _factory_state(
    *,
    has_outline: bool,
    planned: int,
    running_tasks: int,
    blocked_count: int,
    completed: int,
    target: int,
    readiness: Dict[str, Any],
) -> str:
    if not has_outline:
        return "empty"
    if running_tasks > 0:
        return "running"
    if blocked_count > 0:
        return "blocked"
    if target > 0 and completed >= target:
        return "complete"
    if planned <= 0 or readiness["missing"]:
        return "planning"
    return "ready"


@router.get("/api/factory/dashboard")
def get_factory_dashboard() -> Dict[str, Any]:
    root = ws_server.get_root_dir()
    outline = _read_json(root / "workspace" / "outline.json")
    meta = _load_project_meta(root)
    planned = _planned_chapter_count(outline, root)
    target = _target_chapters(outline, meta)
    readiness = _readiness(outline, root, planned)
    completed = _count_completed_chapters(root)
    running_tasks = _running_task_count()
    repair = _repair_summary(root)
    state = _factory_state(
        has_outline=bool(outline),
        planned=planned,
        running_tasks=running_tasks,
        blocked_count=int(repair["blocked_count"]),
        completed=completed,
        target=target,
        readiness=readiness,
    )
    risk_level = "high" if repair["blocked_count"] else ("medium" if readiness["missing"] else "low")
    plan_status = "missing" if not outline else ("ready" if not readiness["missing"] else "planning")
    project_id = ws_server._active_project_id

    return {
        "project": {
            "id": project_id,
            "name": _project_name(project_id, root, outline),
            "scale": str(
                (outline.get("scale_profile") or meta.get("scale_profile") or {}).get("scale")
                or meta.get("scale")
                or "medium"
            ),
            "mode": _infer_mode(meta),
        },
        "production_plan": {
            "status": plan_status,
            "title": _project_name(project_id, root, outline) if outline else "",
            "selling_points": _selling_points(outline),
            "target_chapters": target,
            "planned_chapters": planned,
            "readiness": readiness,
        },
        "factory_status": {
            "state": state,
            "current_stage": "repair" if state == "blocked" else ("writing" if state == "running" else "planning"),
            "completed_chapters": completed,
            "target_chapters": target,
            "running_tasks": running_tasks,
            "risk_level": risk_level,
        },
        "pipeline": _pipeline(state),
        "repair": repair,
        "exports": _exports(root, completed),
    }


@router.put("/api/factory/mode")
def update_factory_mode(req: FactoryModeRequest) -> Dict[str, str]:
    root = ws_server.get_root_dir()
    meta = _load_project_meta(root)
    meta["factory_mode"] = req.mode
    _write_project_meta(root, meta)
    return {"status": "updated", "mode": req.mode}
