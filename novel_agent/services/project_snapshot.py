"""Single project status aggregate shared by HTTP, CLI, MCP, and the desktop UI."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from novel_agent.config.io import ConfigValidationError, load_pipeline_document
from novel_agent.domain.project_snapshot import ProjectSnapshot
from novel_agent.domain.tasks import TaskRecord, TaskStatus
from novel_agent.services.cost_summary import build_cost_summary
from novel_agent.services.novel_run_guard import build_readiness_report
from novel_agent.services.pipeline_pending import collect_pipeline_alerts_cached
from novel_agent.services.progress_summary import build_progress_summary
from novel_agent.state.schema_version import LegacySchemaError
from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

_ACTIVE_TASK_STATUSES = {
    TaskStatus.PENDING,
    TaskStatus.CLAIMED,
    TaskStatus.RUNNING,
    TaskStatus.PAUSED,
}


def _read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, str(exc)
    if not isinstance(value, dict):
        return {}, "document root must be an object"
    return value, None


def _project_details(
    root: Path,
    project_id: str,
    project_info: dict[str, Any] | None,
    meta: dict[str, Any],
    outline: dict[str, Any],
) -> dict[str, Any]:
    info = dict(project_info or {})
    outline_scale = outline.get("scale_profile")
    outline_scale = outline_scale if isinstance(outline_scale, dict) else {}
    meta_scale = meta.get("scale_profile")
    meta_scale = meta_scale if isinstance(meta_scale, dict) else {}
    title = str(
        info.get("name")
        or outline.get("chosen_title")
        or meta.get("name")
        or project_id
    )
    return {
        "id": project_id,
        "name": title,
        "description": str(info.get("description") or meta.get("description") or ""),
        "genre": str(meta.get("genre") or outline.get("genre_positioning") or ""),
        "platform": str(meta.get("platform") or ""),
        "scale": str(
            outline_scale.get("scale")
            or meta_scale.get("scale")
            or meta.get("scale")
            or ""
        ),
        "created_at": info.get("created_at"),
        "updated_at": info.get("updated_at"),
    }


def _workflow_mode(meta: dict[str, Any]) -> str:
    explicit = str(meta.get("workflow_mode") or "").strip().lower()
    if explicit in {"assisted", "factory"}:
        return explicit
    return "factory" if meta.get("factory_mode") else "assisted"


def _outline_progress(
    outline: dict[str, Any],
    *,
    read_error: str | None,
) -> dict[str, Any]:
    arcs = outline.get("macro_outline")
    if not isinstance(arcs, list):
        arcs = []
    try:
        target = max(0, int(outline.get("target_chapters") or 0))
    except (TypeError, ValueError):
        target = 0
    planned = 0
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        chapters = arc.get("chapter_plans")
        if isinstance(chapters, list):
            planned += len(chapters)
    return {
        "exists": bool(outline),
        "valid": read_error is None,
        "title": str(outline.get("chosen_title") or ""),
        "arc_count": len(arcs),
        "planned_chapters": planned,
        "target_chapters": target,
        "error": read_error,
    }


def build_quality_summary(root: Path) -> dict[str, Any]:
    """Aggregate chapter quality reports for every product surface."""
    reports_root = root / "workspace" / "chapters"
    reports = (
        sorted(reports_root.glob("chapter_*/reports/quality.json"))
        if reports_root.is_dir()
        else []
    )
    passed = 0
    failed = 0
    unreadable = 0
    ai_flavor_risks = 0
    latest_issue: dict[str, Any] | None = None
    for report_path in reports:
        report, error = _read_json(report_path)
        chapter_id = report_path.parent.parent.name.removeprefix("chapter_")
        if error:
            unreadable += 1
            latest_issue = {
                "chapter_id": chapter_id,
                "blocked_by": ["quality_report_invalid"],
            }
            continue
        guard = report.get("guard_summary")
        guard = guard if isinstance(guard, dict) else {}
        blocked_by = guard.get("blocked_by")
        blocked_by = blocked_by if isinstance(blocked_by, list) else []
        ai_flavor = report.get("ai_flavor")
        ai_flavor = ai_flavor if isinstance(ai_flavor, dict) else {}
        ai_risk = str(ai_flavor.get("risk_level") or "").lower()
        if "ai_flavor" in blocked_by or ai_risk in {"medium", "high"}:
            ai_flavor_risks += 1
        is_failed = (
            report.get("overall_pass") is False
            or str(guard.get("overall_status") or "").upper() == "FAIL"
        )
        if is_failed:
            failed += 1
            latest_issue = {
                "chapter_id": chapter_id,
                "blocked_by": [str(item) for item in blocked_by],
                "ai_flavor_risk": ai_risk or "unknown",
            }
        else:
            passed += 1
    if failed or unreadable:
        status = "blocked"
    elif reports:
        status = "passed"
    else:
        status = "missing"
    return {
        "status": status,
        "total_reports": len(reports),
        "passed": passed,
        "failed": failed,
        "unreadable": unreadable,
        "ai_flavor_risks": ai_flavor_risks,
        "latest_issue": latest_issue,
    }


def _active_tasks(
    root: Path,
    project_id: str,
) -> tuple[list[TaskRecord], dict[str, Any] | None]:
    try:
        records = SQLiteStateStore(root).task_repository.list_tasks(
            project_id=project_id,
            statuses=_ACTIVE_TASK_STATUSES,
            limit=100,
        )
    except LegacySchemaError as exc:
        return [], {
            "code": "legacy_schema",
            "label": "旧版状态数据库需要备份并重置后才能运行 V2 任务",
            "severity": "error",
            "source": "tasks",
            "detail": str(exc),
        }
    except Exception as exc:
        logger.warning("Failed to read active tasks for %s: %s", root, exc)
        return [], {
            "code": "task_state_unavailable",
            "label": "任务状态暂时不可用",
            "severity": "error",
            "source": "tasks",
            "detail": str(exc),
        }
    # Claim tokens are worker credentials and must never cross a read API boundary.
    return [record.model_copy(update={"claim_token": None}) for record in records], None


def _next_actions(
    readiness: dict[str, Any],
    blocking_issues: list[dict[str, Any]],
    active_tasks: list[TaskRecord],
    outline: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    codes = {str(issue.get("code") or "") for issue in blocking_issues}
    if "config_invalid" in codes:
        actions.append(
            {
                "id": "repair_config",
                "label": "修复配置",
                "kind": "navigate",
                "target": "/settings",
                "enabled": True,
            }
        )
    if not outline:
        actions.append(
            {
                "id": "create_outline",
                "label": "创建故事蓝图",
                "kind": "navigate",
                "target": "/outline",
                "enabled": True,
            }
        )
    if active_tasks:
        actions.append(
            {
                "id": "monitor_tasks",
                "label": "查看运行任务",
                "kind": "navigate",
                "target": "/tasks",
                "enabled": True,
            }
        )
    if blocking_issues and not {"config_invalid", "legacy_schema"}.intersection(codes):
        actions.append(
            {
                "id": "resolve_blocking_issues",
                "label": "处理阻断项",
                "kind": "navigate",
                "target": "/pipeline",
                "enabled": True,
            }
        )
    if not actions:
        actions.append(
            {
                "id": "continue_writing",
                "label": "继续创作",
                "kind": "intent",
                "target": "novel_continue",
                "enabled": bool(readiness.get("ok")) and not active_tasks,
            }
        )
    return actions


def build_project_snapshot(
    root_dir: Path,
    *,
    project_id: str,
    project_info: dict[str, Any] | None = None,
) -> ProjectSnapshot:
    """Build the canonical V2 project snapshot without hiding broken inputs."""

    root = Path(root_dir)
    meta, meta_error = _read_json(root / "config" / "project_meta.json")
    outline, outline_error = _read_json(root / "workspace" / "outline.json")
    blocking_issues: list[dict[str, Any]] = []

    if meta_error:
        blocking_issues.append(
            {
                "code": "project_meta_invalid",
                "label": "项目元数据无法解析",
                "severity": "error",
                "source": "project",
                "detail": meta_error,
            }
        )
    if outline_error:
        blocking_issues.append(
            {
                "code": "outline_invalid",
                "label": "故事蓝图无法解析",
                "severity": "error",
                "source": "outline",
                "detail": outline_error,
            }
        )

    config_error: ConfigValidationError | None = None
    try:
        load_pipeline_document(
            root / "config" / "pipeline.yaml",
            resolve_environment=False,
        )
    except ConfigValidationError as exc:
        config_error = exc
        blocking_issues.append(
            {
                "code": "config_invalid",
                "label": "流水线配置无效",
                "severity": "error",
                "source": "config",
                "errors": exc.errors,
            }
        )

    try:
        readiness = build_readiness_report(root) if config_error is None else {}
    except Exception as exc:
        logger.warning("Failed to build readiness for %s: %s", root, exc)
        readiness = {}
        blocking_issues.append(
            {
                "code": "readiness_unavailable",
                "label": "项目就绪状态无法计算",
                "severity": "error",
                "source": "readiness",
                "detail": str(exc),
            }
        )
    readiness = dict(readiness)
    readiness_pending = readiness.get("pending")
    if isinstance(readiness_pending, list):
        for item in readiness_pending:
            if not isinstance(item, dict):
                continue
            blocking_issues.append(
                {
                    "code": str(item.get("id") or "readiness"),
                    "label": str(item.get("label") or "项目尚未就绪"),
                    "severity": "error",
                    "source": "readiness",
                }
            )
    readiness["ok"] = bool(readiness.get("ok")) and not blocking_issues
    readiness.setdefault("pending", [])
    readiness.setdefault("warnings", [])

    try:
        chapter_progress = build_progress_summary(root)
    except Exception as exc:
        logger.warning("Failed to build chapter progress for %s: %s", root, exc)
        chapter_progress = {
            "authoritative_completed": 0,
            "completed_chapter_ids": [],
            "pending_total": 0,
            "error": str(exc),
        }
        blocking_issues.append(
            {
                "code": "chapter_progress_unavailable",
                "label": "章节进度无法读取",
                "severity": "error",
                "source": "chapters",
                "detail": str(exc),
            }
        )

    active_tasks, task_issue = _active_tasks(root, project_id)
    if task_issue:
        blocking_issues.append(task_issue)

    try:
        alerts = collect_pipeline_alerts_cached(root)
    except Exception as exc:
        logger.warning("Failed to collect pipeline alerts for %s: %s", root, exc)
        alerts = []
    for alert in alerts:
        blocking_issues.append(
            {
                "code": str(alert.get("last_stage") or "pipeline_alert"),
                "label": str(
                    alert.get("message")
                    or alert.get("reason")
                    or f"章节 {alert.get('chapter_id', '')} 待处理"
                ),
                "severity": "error",
                "source": "pipeline",
                "chapter_id": alert.get("chapter_id"),
            }
        )

    try:
        cost_summary = build_cost_summary(root)
    except Exception as exc:
        logger.warning("Failed to build cost summary for %s: %s", root, exc)
        cost_summary = {
            "project_id": project_id,
            "persisted": {
                "call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "total_cost_cny": 0.0,
                "today_tokens": 0,
                "today_cost_cny": 0.0,
            },
            "persisted_error": str(exc),
            "recent_rounds": [],
        }

    return ProjectSnapshot(
        project=_project_details(root, project_id, project_info, meta, outline),
        workflow_mode=_workflow_mode(meta),
        readiness=readiness,
        outline_progress=_outline_progress(outline, read_error=outline_error),
        chapter_progress=chapter_progress,
        active_tasks=active_tasks,
        blocking_issues=blocking_issues,
        quality_summary=build_quality_summary(root),
        cost_summary=cost_summary,
        next_actions=_next_actions(
            readiness,
            blocking_issues,
            active_tasks,
            outline,
        ),
        updated_at=datetime.now(UTC),
    )
