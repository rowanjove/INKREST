"""Tests for batch retry queue and pipeline alert merge."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from novel_agent.agents.base import StaticLLM
from novel_agent.orchestrator import ChapterResult, NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.services.batch_retry_queue import (
    dismiss_batch_retry,
    list_pending_retries,
    record_batch_retry,
)
from novel_agent.services.novel_run_guard import validate_novel_continue
import web.context as web_context
import web.server as web_server
from web.server import app as web_app


def test_record_and_list_pending(tmp_path: Path) -> None:
    record_batch_retry(
        tmp_path,
        chapter_id="007",
        arc_id="A01",
        reason="run_chapter_error",
        message="boom",
    )
    pending = list_pending_retries(tmp_path)
    assert len(pending) == 1
    assert pending[0]["chapter_id"] == "007"
    assert pending[0].get("attempt_count") == 1
    record_batch_retry(
        tmp_path,
        chapter_id="007",
        arc_id="A01",
        reason="run_chapter_error",
        message="again",
    )
    pending = list_pending_retries(tmp_path)
    assert pending[0].get("attempt_count") == 2
    dismiss_batch_retry(tmp_path, "007")
    assert list_pending_retries(tmp_path) == []


def test_merge_arc_preserves_existing_brief(tmp_path: Path) -> None:
    from novel_agent.services.rolling_planner import _merge_arc_chapters

    existing = {
        "arc_id": "A01",
        "chapters": [
            {
                "chapter_id": "001",
                "chapter_title": "稳定标题",
                "chapter_goal": "原目标",
            }
        ],
    }
    incoming = [
        {
            "chapter_id": "001",
            "chapter_title": "新标题",
            "chapter_goal": "新目标",
        },
        {"chapter_id": "002", "chapter_title": "第二章", "chapter_goal": "g2"},
    ]
    merged = _merge_arc_chapters(existing, incoming)
    ch1 = merged["chapters"][0]
    assert ch1["chapter_title"] == "稳定标题"
    assert ch1["chapter_goal"] == "原目标"
    assert any(c["chapter_id"] == "002" for c in merged["chapters"])


@pytest.mark.asyncio
async def test_orchestrator_records_exception_skip(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "pipeline.yaml").write_text(
        "llm:\n  provider: static\nruntime:\n  batch_fail_streak_max: 5\n",
        encoding="utf-8",
    )
    llm = StaticLLM({})
    orch = NovelOrchestrator(PipelineConfig(root_dir=tmp_path, llm=llm))
    orch.chapter_planner = MagicMock()
    orch.chapter_planner.aexpand = AsyncMock(return_value={"detailed_synopsis": "g"})
    orch.arun_chapter = AsyncMock(side_effect=RuntimeError("kaboom"))

    briefs = [{"chapter_id": "003", "goal": "x"}]
    await orch._run_chapter_briefs(briefs, arc_id="A01")
    pending = list_pending_retries(tmp_path)
    assert any(p["chapter_id"] == "003" for p in pending)
    assert pending[0].get("reason") == "run_chapter_error"


def test_pipeline_alerts_include_batch_retry(tmp_path: Path) -> None:
    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = tmp_path
        web_server._active_project_id = None
        web_context._task_manager = None
        record_batch_retry(tmp_path, chapter_id="099", message="skipped in batch")
        client = TestClient(web_app)
        resp = client.get("/api/pipeline-alerts")
        assert resp.status_code == 200
        alerts = resp.json().get("alerts") or []
        assert any(a.get("chapter_id") == "099" and a.get("last_stage") == "batch_retry" for a in alerts)
        dismiss = client.post("/api/pipeline-alerts/099/dismiss")
        assert dismiss.status_code == 200
        assert list_pending_retries(tmp_path) == []
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base


def test_api_continue_rejects_corrupt_outline(tmp_path: Path) -> None:
    from tests.test_full_chain_chaos import _seed_ready

    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = tmp_path
        web_server._active_project_id = None
        web_context._task_manager = None
        _seed_ready(tmp_path)
        (tmp_path / "workspace" / "outline.json").write_text("{bad", encoding="utf-8")
        ok, _ = validate_novel_continue(tmp_path)
        assert not ok
        resp = TestClient(web_app).post(
            "/api/novel/continue",
            json={"dry_run": True, "autopilot": True, "force_resume": True},
        )
        assert resp.status_code == 400
        assert "outline.json" in resp.json().get("detail", "")
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base