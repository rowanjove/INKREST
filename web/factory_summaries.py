"""Factory dashboard aggregation helpers (extracted from routes)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import web.context as ws_server
from web.factory_modes import (
    DEFAULT_FACTORY_MODE,
    factory_mode_label,
    factory_mode_profiles,
    is_valid_factory_mode,
)

logger = logging.getLogger("web.factory_summaries")

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
    return mode if is_valid_factory_mode(mode) else DEFAULT_FACTORY_MODE


def _mode_profile(mode: str) -> Dict[str, Any]:
    profiles = factory_mode_profiles()
    fallback = profiles.get(DEFAULT_FACTORY_MODE, {"mode": DEFAULT_FACTORY_MODE})
    profile = profiles.get(mode, fallback)
    if "label" not in profile:
        profile = {**profile, "label": factory_mode_label(mode)}
    return profile


def _factory_commands(mode: str, state: str, repair: Dict[str, Any], exports: Dict[str, bool]) -> List[Dict[str, str]]:
    commands: List[Dict[str, str]] = []
    if state == "empty":
        commands.append({
            "id": "create_project",
            "label": "新建作品",
            "intent": "create",
            "tone": "primary",
            "reason": "当前还没有可生产的大纲，先进入开书流程。",
        })
    elif state == "planning":
        commands.append({
            "id": "complete_plan",
            "label": "补齐生产计划",
            "intent": "plan",
            "tone": "primary",
            "reason": "生产计划还不完整，先补齐大纲、章节队列和基础资产。",
        })
    elif state == "running":
        commands.append({
            "id": "monitor_production",
            "label": "查看生产进度",
            "intent": "monitor",
            "tone": "primary",
            "reason": "已有任务运行中，优先查看生产线状态。",
        })
    elif state == "blocked" or int(repair.get("blocked_count") or 0) > 0:
        commands.append({
            "id": "repair_blocked",
            "label": "处理阻断章节",
            "intent": "repair",
            "tone": "danger",
            "reason": "存在待修复章节，先处理阻断再继续生产。",
        })
    else:
        commands.append({
            "id": "continue_production",
            "label": "继续生产",
            "intent": "run",
            "tone": "primary",
            "reason": "当前没有阻断，可以继续推进下一批章节。",
        })

    if mode == "platform_review":
        commands.append({
            "id": "export_risk_check",
            "label": "导出前风险总检",
            "intent": "export",
            "tone": "warning",
            "reason": "平台过审模式会优先检查 AI 味、敏感词和投稿风险。",
        })
    elif mode == "longform_stable":
        commands.append({
            "id": "memory_check",
            "label": "检查长篇记忆",
            "intent": "monitor",
            "tone": "warning",
            "reason": "长篇稳定模式建议定期查看设定、伏笔和人物线同步状态。",
        })
    elif mode == "studio":
        commands.append({
            "id": "studio_queue",
            "label": "查看多书队列",
            "intent": "monitor",
            "tone": "info",
            "reason": "工作室生产模式优先关注多项目进度和待处理章节。",
        })

    if exports.get("txt_available") or exports.get("epub_available"):
        commands.append({
            "id": "export_available",
            "label": "导出作品",
            "intent": "export",
            "tone": "success",
            "reason": "已有可导出的章节产物。",
        })
    return commands[:4]


def _operator_brief(
    mode: str,
    state: str,
    repair: Dict[str, Any],
    readiness: Dict[str, Any],
    planned: int,
    completed: int,
    target: int,
) -> Dict[str, str]:
    blocked_items = repair.get("items") if isinstance(repair.get("items"), list) else []
    first_blocked = blocked_items[0] if blocked_items else {}
    missing = readiness.get("missing") if isinstance(readiness.get("missing"), list) else []

    if state == "empty":
        return {
            "severity": "info",
            "next_intent": "create",
            "summary": "还没有可生产的作品，先从开书工厂建立大纲和生产计划。",
            "details": "用户可以只给一个灵感，系统再补齐题材、卖点、角色和章节队列。",
        }
    if state == "planning":
        missing_text = "、".join(str(item) for item in missing[:3]) or "生产计划"
        return {
            "severity": "warning",
            "next_intent": "plan",
            "summary": f"生产计划还缺 {missing_text}，建议先补齐再启动长篇流水线。",
            "details": f"当前已规划 {planned} 章；计划完整后，后续续写更不容易丢设定。",
        }
    if state == "running":
        return {
            "severity": "info",
            "next_intent": "monitor",
            "summary": "生产线正在运行，建议先查看任务进度和实时日志。",
            "details": "此时不要重复启动批量任务，等当前任务结束后系统会刷新产物和风险状态。",
        }
    if state == "blocked":
        chapter_id = str(first_blocked.get("chapter_id") or "")
        title = str(first_blocked.get("title") or f"第 {chapter_id} 章" if chapter_id else "阻断章节")
        return {
            "severity": "danger",
            "next_intent": "repair",
            "summary": f"{title} 需要优先修复，处理后再继续生产。",
            "details": str(first_blocked.get("manual_hint") or "先处理阻断章节，避免后续章节继承错误设定或机器味。"),
        }
    if state == "complete":
        return {
            "severity": "success",
            "next_intent": "export",
            "summary": "目标章节已经完成，可以进入导出和投放前检查。",
            "details": "建议先做通读、风险总检和格式导出，再作为交付稿或投稿稿使用。",
        }

    mode_details = {
        "platform_review": "平台过审模式下，导出前建议重点检查 AI 味、敏感词和重复表达。",
        "longform_stable": "长篇稳定模式下，建议定期检查人物状态、伏笔回收和设定同步。",
        "studio": "工作室模式下，建议关注多书队列、阻断聚合和批量导出节奏。",
        "author_copilot": "作者协作模式下，可以随时人工介入改稿，再让系统继续跑后续章节。",
    }
    progress = f"{completed} / {target}" if target else str(completed)
    return {
        "severity": "success",
        "next_intent": "run",
        "summary": "生产条件已就绪，可以启动或继续下一批章节。",
        "details": mode_details.get(mode, f"当前完成进度 {progress}，系统会优先保持计划、设定和章节队列一致。"),
    }


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


def _production_plan_next_steps(
    readiness: Dict[str, Any],
    *,
    has_outline: bool = True,
) -> List[Dict[str, str]]:
    missing = readiness.get("missing") if isinstance(readiness.get("missing"), list) else []
    catalog = {
        "大纲": {
            "id": "outline",
            "label": "生成大纲",
            "description": "先补齐故事骨架、题材方向和主线承诺。",
            "intent": "plan",
            "route": "/create",
        },
        "书名": {
            "id": "title",
            "label": "补全书名",
            "description": "给作品确定一个可展示、可导出的标题。",
            "intent": "plan",
            "route": "/outline",
        },
        "生产计划": {
            "id": "chapter_queue",
            "label": "补章节队列",
            "description": "把大纲拆成可连续生产的章节目标。",
            "intent": "plan",
            "route": "/outline",
        },
        "角色卡": {
            "id": "character_cards",
            "label": "补角色卡",
            "description": "固定人物动机、关系和说话方式，降低长篇跑偏。",
            "intent": "asset",
            "route": "/assets",
        },
        "世界观": {
            "id": "world_bible",
            "label": "补世界观",
            "description": "沉淀地点、规则、势力和基础设定，给后续章节做参照。",
            "intent": "asset",
            "route": "/assets",
        },
        "风格指南": {
            "id": "style_guide",
            "label": "补风格指南",
            "description": "约束语言口吻、节奏和禁用表达，减少 AI 味。",
            "intent": "asset",
            "route": "/assets",
        },
    }
    steps: List[Dict[str, str]] = []
    if not has_outline:
        steps.append({
            "id": "trope_workshop",
            "label": "从套路工坊开书",
            "description": "组合频道、题材与爽点机制，快速生成可生产设定。",
            "intent": "plan",
            "route": "/trope-workshop",
        })
    for item in missing:
        step = catalog.get(str(item))
        if step:
            steps.append(step)
    return steps[:4]


def _exports(root: Path, completed: int) -> Dict[str, bool]:
    has_text = completed > 0
    return {
        "txt_available": has_text,
        "epub_available": has_text,
        "pdf_available": False,
    }


def _export_check(exports: Dict[str, bool], repair: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    completed_available = bool(exports.get("txt_available") or exports.get("epub_available"))
    blocked_count = int(repair.get("blocked_count") or 0)
    failed = int(quality.get("failed") or 0)
    ai_risks = int(quality.get("ai_flavor_risks") or 0)

    if not completed_available:
        blockers.append("暂无可导出的正式章节")
    if blocked_count > 0:
        blockers.append(f"仍有 {blocked_count} 章待修复")
    if failed > 0:
        blockers.append(f"存在 {failed} 章质检未通过")
    if ai_risks > 0:
        warnings.append(f"发现 {ai_risks} 章 AI 味风险")

    status = "blocked" if blockers else ("warning" if warnings else "ready")
    return {
        "status": status,
        "can_export": completed_available and not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "route": "/workspace",
        "primary_action": "处理阻断" if blockers else "进入导出",
    }


def _chapter_id_from_quality_path(path: Path) -> str:
    chapter_dir = path.parent.parent
    name = chapter_dir.name
    return name.replace("chapter_", "", 1) if name.startswith("chapter_") else name


def _quality_summary(root: Path) -> Dict[str, Any]:
    chapters_root = root / "workspace" / "chapters"
    reports = sorted(chapters_root.glob("chapter_*/reports/quality.json")) if chapters_root.is_dir() else []
    passed = 0
    failed = 0
    ai_flavor_risks = 0
    latest_issue: Dict[str, Any] | None = None

    for report_path in reports:
        report = _read_json(report_path)
        chapter_id = _chapter_id_from_quality_path(report_path)
        guard = report.get("guard_summary") if isinstance(report.get("guard_summary"), dict) else {}
        blocked_by = guard.get("blocked_by") if isinstance(guard.get("blocked_by"), list) else []
        ai_flavor = report.get("ai_flavor") if isinstance(report.get("ai_flavor"), dict) else {}
        ai_risk = str(ai_flavor.get("risk_level") or "").lower()

        if report.get("overall_pass") is False or str(guard.get("overall_status") or "").upper() == "FAIL":
            failed += 1
            latest_issue = {
                "chapter_id": chapter_id,
                "blocked_by": [str(item) for item in blocked_by],
                "ai_flavor_risk": ai_risk or "unknown",
            }
        else:
            passed += 1

        if "ai_flavor" in blocked_by or ai_risk in {"medium", "high"}:
            ai_flavor_risks += 1

    total = len(reports)
    if failed:
        status = "blocked"
    elif total:
        status = "passed"
    else:
        status = "missing"
    return {
        "status": status,
        "total_reports": total,
        "passed": passed,
        "failed": failed,
        "ai_flavor_risks": ai_flavor_risks,
        "latest_issue": latest_issue,
    }


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _quality_report_facts(root: Path) -> Dict[str, Any]:
    chapters_root = root / "workspace" / "chapters"
    reports = sorted(chapters_root.glob("chapter_*/reports/quality.json")) if chapters_root.is_dir() else []
    facts: Dict[str, Any] = {
        "total": 0,
        "failed": 0,
        "ai_flavor": 0,
        "style": 0,
        "platform": 0,
        "continuity": 0,
        "state": 0,
        "samples": [],
    }
    for report_path in reports:
        report = _read_json(report_path)
        chapter_id = _chapter_id_from_quality_path(report_path)
        guard = report.get("guard_summary") if isinstance(report.get("guard_summary"), dict) else {}
        blocked_by = [str(item) for item in guard.get("blocked_by", [])] if isinstance(guard.get("blocked_by"), list) else []
        ai_flavor = report.get("ai_flavor") if isinstance(report.get("ai_flavor"), dict) else {}
        ai_risk = str(ai_flavor.get("risk_level") or "").lower()
        failed = report.get("overall_pass") is False or str(guard.get("overall_status") or "").upper() == "FAIL"

        facts["total"] += 1
        if failed:
            facts["failed"] += 1
        if "ai_flavor" in blocked_by or ai_risk in {"medium", "high"}:
            facts["ai_flavor"] += 1
        if "style" in blocked_by:
            facts["style"] += 1
        if any(item in blocked_by for item in ("sensitive", "platform", "compliance")):
            facts["platform"] += 1
        if "continuity" in blocked_by:
            facts["continuity"] += 1
        if "state" in blocked_by or "memory" in blocked_by:
            facts["state"] += 1
        if blocked_by and len(facts["samples"]) < 3:
            facts["samples"].append({"chapter_id": chapter_id, "blocked_by": blocked_by, "ai_flavor_risk": ai_risk})
    return facts


def _tracked_state_counts(root: Path) -> Dict[str, int]:
    counts = {"characters": 0, "foreshadows": 0, "reader_promises": 0, "secrets": 0}
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        store = SQLiteStateStore(root)
        counts["characters"] = len(store.list_characters())
        counts["foreshadows"] = len(store.list_foreshadows())
        counts["reader_promises"] = len(store.list_reader_promises())
        counts["secrets"] = len(store.list_secrets())
    except Exception:
        pass
    return counts


def _stability_report(
    root: Path,
    outline: Dict[str, Any],
    planned: int,
    target: int,
    completed: int,
    quality_facts: Dict[str, Any],
) -> Dict[str, Any]:
    empty_tracked = {"characters": 0, "foreshadows": 0, "reader_promises": 0, "secrets": 0}
    if not outline:
        return {
            "status": "missing",
            "score": 0,
            "summary": "No production plan exists yet.",
            "tracked": empty_tracked,
            "risks": [],
            "next_actions": [
                {
                    "id": "create_plan",
                    "label": "Create production plan",
                    "intent": "plan",
                    "route": "/create",
                    "reason": "A longform stability report needs an outline first.",
                }
            ],
        }

    score = 100
    risks: List[Dict[str, str]] = []
    tracked = _tracked_state_counts(root)

    def add_risk(risk_id: str, label: str, severity: str, detail: str, route: str, action_label: str, penalty: int) -> None:
        nonlocal score
        score -= penalty
        risks.append(
            {
                "id": risk_id,
                "label": label,
                "severity": severity,
                "detail": detail,
                "route": route,
                "action_label": action_label,
            }
        )

    if planned <= 0:
        add_risk(
            "chapter_plan_missing",
            "Chapter plan missing",
            "danger",
            "The outline has no chapter queue for continuous production.",
            "/outline",
            "Open outline",
            12,
        )
    if not (root / "assets" / "character_cards.yaml").is_file():
        add_risk(
            "character_cards_missing",
            "Character cards missing",
            "warning",
            "Character cards reduce personality and state drift in longform runs.",
            "/assets",
            "Open assets",
            12,
        )
    if not (root / "assets" / "world_bible.md").is_file():
        add_risk(
            "world_bible_missing",
            "World bible missing",
            "warning",
            "A world bible keeps settings, forces, and rules consistent.",
            "/assets",
            "Open assets",
            10,
        )
    if not (root / "assets" / "style_guide.md").is_file():
        add_risk(
            "style_guide_missing",
            "Style guide missing",
            "info",
            "A style guide makes later chapters less likely to drift in voice.",
            "/assets",
            "Open assets",
            8,
        )
    if planned > 0 and completed <= 0:
        add_risk(
            "no_completed_chapters",
            "No completed chapters",
            "info",
            "Stability confidence improves after at least one completed chapter is audited.",
            "/workspace",
            "Open workbench",
            8,
        )

    continuity_failures = int(quality_facts.get("continuity") or 0) + int(quality_facts.get("state") or 0)
    if continuity_failures:
        add_risk(
            "continuity_failures",
            "Continuity failures",
            "danger",
            f"{continuity_failures} chapter report(s) mention continuity or state problems.",
            "/chapters/maintenance?expand=alerts",
            "Open repair queue",
            min(30, continuity_failures * 10),
        )
    if target >= 100 and sum(tracked.values()) < 3:
        add_risk(
            "low_longform_memory",
            "Low longform memory coverage",
            "warning",
            "This project targets 100+ chapters but has very little tracked story memory.",
            "/state",
            "Open state library",
            5,
        )

    status = "blocked" if any(risk["severity"] == "danger" for risk in risks) else ("warning" if risks else "stable")
    primary_risk = risks[0] if risks else None
    return {
        "status": status,
        "score": _clamp_score(score),
        "summary": "Longform stability is ready." if status == "stable" else "Longform stability needs attention before large batch production.",
        "tracked": tracked,
        "risks": risks,
        "next_actions": [
            {
                "id": "stability_next",
                "label": primary_risk["action_label"] if primary_risk else "Continue production",
                "intent": "state" if primary_risk and primary_risk["route"] == "/state" else "asset",
                "route": primary_risk["route"] if primary_risk else "/workspace",
                "reason": primary_risk["detail"] if primary_risk else "No stability blocker is visible.",
            }
        ],
    }


def _naturalness_report(quality_facts: Dict[str, Any], completed: int) -> Dict[str, Any]:
    total = int(quality_facts.get("total") or 0)
    if total <= 0:
        return {
            "status": "missing",
            "score": 92 if completed <= 0 else 84,
            "summary": "No quality reports are available yet.",
            "risk_types": [],
            "sample_issues": [],
            "next_actions": [
                {
                    "id": "run_quality",
                    "label": "Run quality check",
                    "intent": "monitor",
                    "route": "/workspace",
                    "reason": "Naturalness confidence needs quality reports.",
                }
            ],
        }

    failed = int(quality_facts.get("failed") or 0)
    ai_flavor = int(quality_facts.get("ai_flavor") or 0)
    style = int(quality_facts.get("style") or 0)
    platform = int(quality_facts.get("platform") or 0)
    score = 100 - min(45, failed * 15) - min(36, ai_flavor * 12) - min(30, style * 10) - min(30, platform * 10)
    risk_types: List[Dict[str, Any]] = []
    for risk_id, label, count in (
        ("ai_flavor", "AI flavor", ai_flavor),
        ("style", "Style risk", style),
        ("platform", "Platform-facing risk", platform),
    ):
        if count:
            risk_types.append({"id": risk_id, "label": label, "count": count, "severity": "warning" if not failed else "danger"})

    samples: List[Dict[str, str]] = []
    for sample in quality_facts.get("samples", [])[:3]:
        chapter_id = str(sample.get("chapter_id") or "")
        blocked_by = sample.get("blocked_by") if isinstance(sample.get("blocked_by"), list) else []
        samples.append(
            {
                "chapter_id": chapter_id,
                "label": " / ".join(str(item) for item in blocked_by) or "Quality risk",
                "detail": f"Quality report flagged: {', '.join(str(item) for item in blocked_by)}",
                "route": f"/chapters/{chapter_id}",
            }
        )

    status = "blocked" if failed and risk_types else ("warning" if risk_types else "natural")
    return {
        "status": status,
        "score": _clamp_score(score),
        "summary": "Naturalness risk is under control." if status == "natural" else "Naturalness or platform-facing risk exists in quality reports.",
        "risk_types": risk_types,
        "sample_issues": samples,
        "next_actions": [
            {
                "id": "naturalness_next",
                "label": "Reduce AI flavor",
                "intent": "repair",
                "route": "/workspace",
                "reason": "Use repair actions or manual edit hints before export.",
            }
        ]
        if risk_types
        else [
            {
                "id": "naturalness_ready",
                "label": "Export preflight",
                "intent": "export",
                "route": "/workspace",
                "reason": "No visible naturalness risk is blocking export.",
            }
        ],
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



def build_factory_dashboard(root: Path, project_id: str | None, running_tasks: int) -> Dict[str, Any]:
    outline = _read_json(root / "workspace" / "outline.json")
    meta = _load_project_meta(root)
    planned = _planned_chapter_count(outline, root)
    target = _target_chapters(outline, meta)
    readiness = _readiness(outline, root, planned)
    completed = _count_completed_chapters(root)
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
    mode = _infer_mode(meta)
    exports = _exports(root, completed)
    quality_summary = _quality_summary(root)
    quality_facts = _quality_report_facts(root)
    stability_report = _stability_report(root, outline, planned, target, completed, quality_facts)
    naturalness_report = _naturalness_report(quality_facts, completed)
    return {
        "project": {
            "id": project_id,
            "name": _project_name(project_id, root, outline),
            "author_label": str(meta.get("author_label") or "").strip(),
            "scale": str(
                (outline.get("scale_profile") or meta.get("scale_profile") or {}).get("scale")
                or meta.get("scale")
                or "medium"
            ),
            "mode": mode,
        },
        "production_plan": {
            "status": plan_status,
            "title": _project_name(project_id, root, outline) if outline else "",
            "selling_points": _selling_points(outline),
            "target_chapters": target,
            "planned_chapters": planned,
            "readiness": readiness,
            "next_steps": _production_plan_next_steps(readiness, has_outline=bool(outline)),
        },
        "factory_status": {
            "state": state,
            "current_stage": "repair" if state == "blocked" else ("writing" if state == "running" else "planning"),
            "completed_chapters": completed,
            "target_chapters": target,
            "running_tasks": running_tasks,
            "risk_level": risk_level,
        },
        "mode_profile": _mode_profile(mode),
        "operator_brief": _operator_brief(mode, state, repair, readiness, planned, completed, target),
        "commands": _factory_commands(mode, state, repair, exports),
        "pipeline": _pipeline(state),
        "quality_summary": quality_summary,
        "export_check": _export_check(exports, repair, quality_summary),
        "stability_report": stability_report,
        "naturalness_report": naturalness_report,
        "repair": repair,
        "exports": exports,
    }


def summarize_project_book(
    project_id: str,
    project_dir: Path,
    info: Dict[str, Any],
    *,
    running_tasks: int = 0,
) -> Dict[str, Any]:
    root = project_dir
    outline = _read_json(root / "workspace" / "outline.json")
    meta = _load_project_meta(root)
    planned = _planned_chapter_count(outline, root)
    target = _target_chapters(outline, meta)
    readiness = _readiness(outline, root, planned)
    completed = _count_completed_chapters(root)
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
    return {
        "id": project_id,
        "name": _project_name(project_id, root, outline),
        "author_label": str(meta.get("author_label") or "").strip(),
        "genre": str(meta.get("genre") or "").strip(),
        "scale": str(
            (outline.get("scale_profile") or meta.get("scale_profile") or {}).get("scale")
            or meta.get("scale")
            or "medium"
        ),
        "factory_state": state,
        "kanban_column": state,
        "completed_chapters": completed,
        "target_chapters": target,
        "planned_chapters": planned,
        "blocked_count": int(repair["blocked_count"]),
        "pending_alert_count": int(info.get("pending_alert_count") or 0),
        "risk_level": risk_level,
        "pinned": bool(info.get("pinned")),
        "updated_at": str(info.get("updated_at") or info.get("activity_at") or ""),
        "is_demo": bool(meta.get("is_demo")),
    }
