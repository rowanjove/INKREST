from __future__ import annotations

import json
from pathlib import Path

from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.services.production_workspace import build_production_workspace
from novel_agent.services.quality_review import build_quality_review_queue
from novel_agent.state.sqlite_store import SQLiteStateStore


def _seed_project(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "config" / "pipeline.yaml").write_text(
        "schema_version: 2\n"
        "runtime:\n  max_workers: 2\n"
        "chapter:\n  default_target_chars: [1200, 2200]\n"
        "llm:\n  provider: static\n"
        "embedding:\n  provider: stub\n",
        encoding="utf-8",
    )
    (root / "config" / "project_meta.json").write_text(
        json.dumps({"workflow_mode": "factory"}),
        encoding="utf-8",
    )
    (root / "workspace").mkdir(parents=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "chosen_title": "生产中心测试",
                "target_chapters": 20,
                "macro_outline": [{"arc_id": "A01", "chapter_plans": []}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _seed_blocked_quality(root: Path) -> None:
    chapter = root / "workspace" / "chapters" / "chapter_003"
    reports = chapter / "reports"
    reports.mkdir(parents=True)
    (chapter / "plan.json").write_text(
        json.dumps({"chapter_title": "第三章 门后的影子"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": "003",
                "last_stage": "quality_blocked",
                "completed_stages": ["writer", "auditor"],
                "timestamp": 10,
            }
        ),
        encoding="utf-8",
    )
    (reports / "quality.json").write_text(
        json.dumps(
            {
                "overall_score": 48,
                "overall_pass": False,
                "checks": {
                    "style": {
                        "pass": False,
                        "score": 42,
                        "level": "fail",
                        "details": ["句式重复"],
                    }
                },
                "guard_summary": {
                    "overall_status": "FAIL",
                    "blocked_by": ["style"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_quality_review_queue_normalizes_reports_and_alerts(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    _seed_blocked_quality(tmp_path)

    queue = build_quality_review_queue(tmp_path)

    assert queue["summary"]["open_items"] == 1
    item = queue["items"][0]
    assert item["chapter_id"] == "003"
    assert item["chapter_title"] == "第三章 门后的影子"
    assert item["stage"] == "quality_blocked"
    assert item["stage_label"] == "质量阻断"
    assert item["overall_score"] == 48
    assert item["recommended_action"] == "edit_then_gate"
    assert item["issues"][0]["code"] == "style"
    assert item["issues"][0]["label"] == "文风与表达"
    assert item["issues"][0]["details"] == ["句式重复"]


def test_quality_review_queue_surfaces_malformed_report(tmp_path: Path) -> None:
    _seed_project(tmp_path)
    report = (
        tmp_path
        / "workspace"
        / "chapters"
        / "chapter_004"
        / "reports"
        / "quality.json"
    )
    report.parent.mkdir(parents=True)
    report.write_text("{broken", encoding="utf-8")

    queue = build_quality_review_queue(tmp_path)

    assert queue["summary"]["unreadable"] == 1
    assert queue["items"][0]["issues"][0]["code"] == "quality_report_invalid"
    assert "quality.json" not in queue["items"][0]["issues"][0]["details"][0]


def test_production_workspace_uses_snapshot_and_sanitized_task_history(
    tmp_path: Path,
) -> None:
    root = tmp_path / "book-1"
    _seed_project(root)
    _seed_blocked_quality(root)
    store = SQLiteStateStore(root)
    store.task_repository.create_task(
        task_id="task-1",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "003", "goal": "修复章节"},
        max_attempts=2,
    )
    claimed = store.task_repository.claim_task("task-1")
    assert claimed and claimed.claim_token
    running = store.task_repository.start_task("task-1", claimed.claim_token)
    store.task_repository.heartbeat(
        running.id,
        claimed.claim_token,
        checkpoint={
            "chapter_id": "003",
            "step": "auditor",
            "resumable_from": "audit",
        },
    )
    store.task_repository.append_task_log(
        "task-1",
        level="warning",
        step="auditor",
        message="审校发现阻断",
    )
    store.task_repository.finish_task(
        "task-1",
        claimed.claim_token,
        status=TaskStatus.FAILED,
        result={"code": "QUALITY_BLOCKED", "failure_hint": "先修稿再重试"},
        reason="quality_blocked",
    )

    workspace = build_production_workspace(
        root,
        project_id="book-1",
        project_info={"name": "生产中心测试"},
    ).model_dump(mode="json")

    assert workspace["schema_version"] == 1
    assert workspace["snapshot"]["project"]["id"] == "book-1"
    assert workspace["snapshot"]["quality_summary"]["failed"] == 1
    task = workspace["tasks"][0]
    assert task["id"] == "task-1"
    assert task["status_label"] == "失败"
    assert task["task_type_label"] == "单章生产"
    assert task["chapter_id"] == "003"
    assert task["recovery_action"] == "resume_audit"
    assert "claim_token" not in task
    assert workspace["events"][0]["to_status"] == "failed"
    assert workspace["task_logs"][0]["message"] == "审校发现阻断"
    assert workspace["reviews"]["items"][0]["chapter_id"] == "003"
    assert workspace["section_errors"] == {}
