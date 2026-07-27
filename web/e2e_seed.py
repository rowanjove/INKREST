"""Deterministic Playwright / CI fixture data (no LLM)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from novel_agent.domain.tasks import TaskStatus
from novel_agent.services.arc_queue import record_novel_batch_paused
from novel_agent.services.batch_retry_queue import record_batch_retry
from novel_agent.services.outline_sync import mark_arcs_synced_with_outline
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection
from tests.helpers.seed_engine import seed_usable_daily_model

E2E_PROJECT_NAME = "E2E维护场景"


def _seed_ready_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: e2e-daily\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    seed_usable_daily_model(root, model_id="e2e-daily")
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 40, encoding="utf-8")
    outline = {
        "chosen_title": "E2E修章测试书",
        "target_chapters": 20,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-10", "goal": "e2e"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps(
            {
                "arc_id": "A01",
                "chapters": [
                    {"chapter_id": "001", "chapter_goal": "ok"},
                    {"chapter_id": "002", "chapter_goal": "retry"},
                    {"chapter_id": "003", "chapter_goal": "gate"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    mark_arcs_synced_with_outline(root)


def _seed_manuscript_chapters(root: Path) -> None:
    chapters = {
        "001": ("第一章 雨夜来信", "雨落在旧城的青石路上。\n\n林越推开门，发现桌上多了一封没有署名的信。"),
        "002": ("第二章 失踪的钟声", "午夜钟声响起时，城北的灯一盏接一盏熄灭。"),
        "003": ("第三章 门后的影子", "门缝里没有光，只有一阵很轻的呼吸声。"),
    }
    for chapter_id, (title, text) in chapters.items():
        chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        (chapter_dir / "plan.json").write_text(
            json.dumps(
                {
                    "chapter_id": chapter_id,
                    "chapter_title": title,
                    "chapter_goal": "推进调查并留下下一章悬念",
                    "detailed_synopsis": "主角沿着新线索继续调查旧城异象。",
                    "target_chars": [1800, 2600],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (chapter_dir / "chapter_final.txt").write_text(text, encoding="utf-8")

    store = SQLiteStateStore(root)
    for chapter_id, (title, text) in chapters.items():
        chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
        store.index_chapter(
            chapter_id,
            title,
            chapter_dir / "chapter_final.txt",
            len(text.replace("\n", "")),
            "high" if chapter_id == "003" else "",
            has_final=1,
            gate_status="failed" if chapter_id == "003" else "ready",
            indexed_at=time.time(),
        )
    with safe_connection(store.db_path) as conn:
        with conn:
            conn.execute(
                "delete from document_revisions where chapter_id in ('001', '002', '003')"
            )
            conn.execute(
                "delete from documents where chapter_id in ('001', '002', '003')"
            )


def _seed_quality_blocked_chapter(root: Path, chapter_id: str = "003") -> None:
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    reports = chapter_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "chapter_id": chapter_id,
                "last_stage": "quality_blocked",
                "completed_stages": ["writer", "auditor"],
                "timestamp": time.time(),
            },
            ensure_ascii=False,
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
                        "details": ["连续短句过多，段落节奏需要调整。"],
                    }
                },
                "guard_summary": {"overall_status": "FAIL", "blocked_by": ["style"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _seed_production_history(root: Path, project_id: str) -> list[str]:
    store = SQLiteStateStore(root)
    repo = store.task_repository
    task_ids = [
        "e2e-production-queued",
        "e2e-production-failed",
        "e2e-production-done",
    ]
    with safe_connection(store.db_path) as conn:
        with conn:
            for task_id in task_ids:
                conn.execute("delete from task_logs where task_id = ?", (task_id,))
                conn.execute(
                    "delete from task_status_events where task_id = ?", (task_id,)
                )
                conn.execute("delete from tasks where id = ?", (task_id,))

    repo.create_task(
        task_id=task_ids[0],
        project_id=project_id,
        task_type="export",
        payload={"goal": "等待导出审校样稿"},
    )

    repo.create_task(
        task_id=task_ids[1],
        project_id=project_id,
        task_type="chapter",
        payload={"chapter_id": "003", "goal": "修订门后影子章节"},
        max_attempts=1,
    )
    claimed = repo.claim_task(task_ids[1])
    assert claimed is not None and claimed.claim_token
    repo.start_task(task_ids[1], claimed.claim_token)
    repo.append_task_log(
        task_ids[1],
        message="正文已完成，进入质量门禁",
        step="quality_guard",
    )
    repo.heartbeat(
        task_ids[1],
        claimed.claim_token,
        checkpoint={
            "resumable_from": "audit",
            "progress": {"step": "quality_guard", "chapter_id": "003"},
        },
    )
    repo.finish_task(
        task_ids[1],
        claimed.claim_token,
        status=TaskStatus.FAILED,
        result={
            "error": {
                "code": "quality_blocked",
                "message": "文风与表达未达到质量门禁要求",
            }
        },
        reason="quality_blocked",
    )
    repo.append_task_log(
        task_ids[1],
        level="error",
        message="文风与表达未达到质量门禁要求",
        step="quality_guard",
    )

    repo.create_task(
        task_id=task_ids[2],
        project_id=project_id,
        task_type="export",
        payload={"goal": "生成审校预览"},
    )
    done = repo.claim_task(task_ids[2])
    assert done is not None and done.claim_token
    repo.start_task(task_ids[2], done.claim_token)
    repo.append_task_log(
        task_ids[2],
        message="审校预览已生成",
        step="export",
    )
    repo.finish_task(
        task_ids[2],
        done.claim_token,
        status=TaskStatus.SUCCEEDED,
        result={"format": "preview"},
        reason="completed",
    )

    from web.runtime_log_buffer import (
        append_runtime_log,
        clear_runtime_logs,
    )

    clear_runtime_logs(project_id=project_id)
    append_runtime_log(
        {
            "type": "progress",
            "project_id": project_id,
            "task_id": task_ids[1],
            "chapter_id": "003",
            "step": "quality_guard",
            "status": "blocked",
            "message": "第 003 章质量门禁阻断",
        }
    )
    append_runtime_log(
        {
            "type": "log",
            "project_id": project_id,
            "task_id": task_ids[2],
            "step": "export",
            "message": "审校预览已生成",
        }
    )
    return task_ids


def seed_maintenance_scenario(project_manager) -> Dict[str, Any]:
    """Create or refresh fixture project with repair queue + paused batch."""
    existing_id = None
    for row in project_manager.list_projects():
        if row.get("name") == E2E_PROJECT_NAME:
            existing_id = row.get("id")
            break

    if existing_id:
        project_id = str(existing_id)
        root = project_manager.base_dir / "projects" / project_id
    else:
        created = project_manager.create_project(E2E_PROJECT_NAME, "Playwright E2E fixture")
        project_id = str(created["id"])
        root = project_manager.base_dir / "projects" / project_id

    _seed_ready_project(root)
    _seed_manuscript_chapters(root)
    record_batch_retry(
        root,
        chapter_id="002",
        arc_id="A01",
        reason="run_chapter_error",
        step="run_chapter",
        message="E2E fixture batch skip",
    )
    _seed_quality_blocked_chapter(root, "003")
    record_novel_batch_paused(
        root,
        reason="quality_blocked",
        last_chapter="003",
        arc_id="A01",
        streak=1,
    )
    production_task_ids = _seed_production_history(root, project_id)

    try:
        from novel_agent.services.pipeline_pending import (
            invalidate_pipeline_alerts_cache,
            summarize_pipeline_pending,
        )

        invalidate_pipeline_alerts_cache(root)
        pending = summarize_pipeline_pending(root)
    except Exception:
        pending = {"pending_total": 0}

    return {
        "project_id": project_id,
        "project_name": E2E_PROJECT_NAME,
        "batch_paused": True,
        "pause_reason": "quality_blocked",
        "last_chapter_id": "003",
        "pending_chapter_ids": ["002", "003"],
        "pending_total": int(pending.get("pending_total") or 0),
        "production_task_ids": production_task_ids,
    }
