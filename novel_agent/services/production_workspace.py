"""Build the single production-center aggregate."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from novel_agent.domain.production import ProductionWorkspace
from novel_agent.domain.tasks import TaskRecord, TaskStatus, TaskType
from novel_agent.services.project_snapshot import build_project_snapshot
from novel_agent.services.quality_review import build_quality_review_queue
from novel_agent.state.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

TASK_STATUS_LABELS = {
    TaskStatus.PENDING: "等待中",
    TaskStatus.CLAIMED: "已领取",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.PAUSED: "已暂停",
    TaskStatus.SUCCEEDED: "已完成",
    TaskStatus.FAILED: "失败",
    TaskStatus.CANCELLED: "已取消",
}

TASK_TYPE_LABELS = {
    TaskType.CHAPTER: "单章生产",
    TaskType.CHAPTER_BATCH: "章节批处理",
    TaskType.NOVEL_PLAN: "全书规划",
    TaskType.CHAPTER_PLAN: "章节规划",
    TaskType.NOVEL_RUN: "全书生产",
    TaskType.ARC_RUN: "分卷生产",
    TaskType.NOVEL_CONTINUE: "继续写书",
    TaskType.NOVEL_AUTOPILOT: "自动连写",
    TaskType.EMBEDDING_SETUP: "记忆索引",
    TaskType.EXPORT: "导出",
}

STEP_LABELS = {
    "init": "初始化",
    "chapter_planner": "章节规划",
    "writer": "正文写作",
    "merge": "场景合并",
    "stitch_editor": "接缝修复",
    "style_editor": "文风优化",
    "continuity_checker": "连续性检查",
    "chapter_summary": "章节总结",
    "auditor": "审校",
    "state_extractor": "状态提取",
    "rewriter": "问题改写",
    "length_fix": "字数修复",
    "unified_gate": "统一门禁",
    "quality_guard": "质量门禁",
    "approval": "人工审批",
    "sensitive_scan": "敏感词检查",
    "state_update": "状态同步",
    "vector_index": "记忆索引",
    "plugin_hook": "插件钩子",
}

_ACTIVE = {
    TaskStatus.PENDING,
    TaskStatus.CLAIMED,
    TaskStatus.RUNNING,
    TaskStatus.PAUSED,
}
_AUDIT_STEPS = {
    "auditor",
    "rewriter",
    "unified_gate",
    "quality_guard",
    "approval",
}


def _task_view(task: TaskRecord) -> dict[str, Any]:
    payload = dict(task.payload_json)
    checkpoint = dict(task.checkpoint or {})
    result = dict(task.result_json or {})
    progress = checkpoint.get("progress")
    progress = progress if isinstance(progress, dict) else {}
    chapter_id = str(
        payload.get("chapter_id")
        or checkpoint.get("chapter_id")
        or progress.get("chapter_id")
        or ""
    )
    step = str(checkpoint.get("step") or progress.get("step") or "")
    resumable_from = str(checkpoint.get("resumable_from") or "")
    if task.status in _ACTIVE:
        recovery_action = "cancel"
    elif task.status in {TaskStatus.FAILED, TaskStatus.PAUSED} and (
        resumable_from or step in _AUDIT_STEPS
    ):
        recovery_action = "resume_audit"
    elif task.status is TaskStatus.FAILED and chapter_id:
        recovery_action = "open_writer"
    else:
        recovery_action = "none"
    failure_message = str(
        result.get("failure_hint")
        or result.get("message")
        or result.get("_error")
        or task.status_reason
        or ""
    )
    return {
        "id": task.id,
        "project_id": task.project_id,
        "task_type": task.task_type.value,
        "task_type_label": TASK_TYPE_LABELS.get(task.task_type, task.task_type.value),
        "status": task.status.value,
        "status_label": TASK_STATUS_LABELS.get(task.status, task.status.value),
        "chapter_id": chapter_id or None,
        "goal": str(payload.get("goal") or ""),
        "attempt": task.attempt,
        "max_attempts": task.max_attempts,
        "step": step or None,
        "step_label": STEP_LABELS.get(step, step) if step else None,
        "checkpoint": {
            "resumable_from": resumable_from or None,
            "progress": progress or None,
        },
        "status_reason": task.status_reason,
        "failure_code": str(result.get("code") or "") or None,
        "failure_message": failure_message or None,
        "recovery_action": recovery_action,
        "heartbeat_at": task.heartbeat_at,
        "lease_expires_at": task.lease_expires_at,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def _event_view(event: dict[str, Any]) -> dict[str, Any]:
    target = str(event.get("to_status") or "")
    source = str(event.get("from_status") or "")
    return {
        **event,
        "from_status_label": TASK_STATUS_LABELS.get(
            TaskStatus(source), source
        )
        if source
        else None,
        "to_status_label": TASK_STATUS_LABELS.get(TaskStatus(target), target),
    }


def build_production_workspace(
    root_dir: Path,
    *,
    project_id: str,
    project_info: dict[str, Any] | None = None,
    task_limit: int = 100,
    event_limit: int = 300,
    log_limit: int = 300,
) -> ProductionWorkspace:
    root = Path(root_dir)
    snapshot = build_project_snapshot(
        root,
        project_id=project_id,
        project_info=project_info,
    )
    tasks: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    task_logs: list[dict[str, Any]] = []
    runtime_logs: list[dict[str, Any]] = []
    section_errors: dict[str, str] = {}

    try:
        repository = SQLiteStateStore(root).task_repository
        records = repository.list_tasks(project_id=project_id, limit=task_limit)
        tasks = [_task_view(record) for record in records]
        events = [
            _event_view(event)
            for event in repository.list_task_status_events(
                project_id=project_id,
                limit=event_limit,
            )
        ]
        task_logs = repository.list_task_logs(
            project_id=project_id,
            limit=log_limit,
        )
    except Exception as exc:
        logger.warning("Failed to build production task history for %s: %s", root, exc)
        section_errors["tasks"] = "任务历史暂时不可用"

    try:
        reviews = build_quality_review_queue(root)
    except Exception as exc:
        logger.warning("Failed to build quality review queue for %s: %s", root, exc)
        reviews = {
            "summary": {
                **snapshot.quality_summary,
                "open_items": 0,
                "stage_counts": {},
            },
            "items": [],
        }
        section_errors["reviews"] = "审校队列暂时不可用"

    try:
        from web.runtime_log_buffer import tail_runtime_logs

        runtime_logs = tail_runtime_logs(log_limit, project_id=project_id)
    except Exception as exc:
        logger.warning("Failed to read runtime logs for %s: %s", root, exc)
        section_errors["runtime_logs"] = "实时日志暂时不可用"

    return ProductionWorkspace(
        snapshot=snapshot,
        tasks=tasks,
        events=events,
        task_logs=task_logs,
        runtime_logs=runtime_logs,
        reviews=reviews,
        section_errors=section_errors,
        updated_at=datetime.now(UTC),
    )
