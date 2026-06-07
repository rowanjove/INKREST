"""Deterministic Playwright / CI fixture data (no LLM)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from novel_agent.services.arc_queue import record_novel_batch_paused
from novel_agent.services.batch_retry_queue import record_batch_retry
from novel_agent.services.outline_sync import mark_arcs_synced_with_outline
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
                "overall_pass": False,
                "guard_summary": {"overall_status": "FAIL", "blocked_by": ["test_guard"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


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
    }