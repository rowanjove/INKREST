"""
全书链路混沌 / 压力测试（无真实 LLM）。

覆盖：开书门槛、continue 并发、熔断、卷队列脏数据、待处理扫描、TaskManager 去重。
"""

from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from novel_agent.orchestrator import ChapterResult, NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.services.arc_queue import record_novel_batch_paused
from novel_agent.services.batch_retry_queue import list_pending_retries
from novel_agent.services.novel_run_guard import build_readiness_report, validate_novel_continue
from novel_agent.services.outline_sync import check_arc_queue_stale, mark_arcs_synced_with_outline
from novel_agent.agents.base import StaticLLM
from tests.helpers.seed_engine import seed_usable_daily_model
from web.tasks import TaskManager
import web.context as web_context
import web.server as web_server
from web.server import app as web_app


def _reset_task_manager() -> None:
    web_context._task_manager = None


def _seed_ready(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: chaos-daily\nruntime:\n  max_workers: 1\n  batch_fail_streak_max: 3\n",
        encoding="utf-8",
    )
    seed_usable_daily_model(root, model_id="chaos-daily")
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 40, encoding="utf-8")
    outline = {
        "chosen_title": "混沌测试",
        "target_chapters": 50,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-20", "goal": "g"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps(
            {
                "arc_id": "A01",
                "chapters": [{"chapter_id": f"{i:03d}", "goal": "beat"} for i in range(1, 21)],
            }
        ),
        encoding="utf-8",
    )
    mark_arcs_synced_with_outline(root)


# --- 1. 脏数据韧性 ---


def test_readiness_never_crashes_on_corrupt_workspace(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    (tmp_path / "workspace" / "outline.json").write_text("{broken json", encoding="utf-8")
    (tmp_path / "assets" / "rules.md").write_bytes(b"")
    report = build_readiness_report(tmp_path)
    assert isinstance(report, dict)
    ok, detail = validate_novel_continue(tmp_path)
    assert isinstance(ok, bool)
    assert isinstance(detail, str)


def test_corrupt_outline_blocks_stale_and_continue(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    (tmp_path / "workspace" / "outline.json").write_text("not-json", encoding="utf-8")
    stale = check_arc_queue_stale(tmp_path)
    assert stale.get("reason") == "outline_read_error"
    assert stale.get("stale") is True
    ok, detail = validate_novel_continue(tmp_path)
    assert not ok
    assert "outline.json" in detail


def test_macro_changed_without_sync_blocks_continue(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    outline = json.loads((tmp_path / "workspace" / "outline.json").read_text(encoding="utf-8"))
    outline["macro_outline"].append({"arc_id": "A99", "chapters": "21-30", "goal": "new"})
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    ok, detail = validate_novel_continue(tmp_path)
    assert not ok
    assert "卷" in detail or "队列" in detail or "同步" in detail


# --- 2. API 层暴力 ---


class _ApiChaosBase:
    def _with_project(self, fn):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            _seed_ready(self.tmpdir)
            return fn(TestClient(web_app))
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base


@pytest.fixture
def api_tmp(tmp_path: Path):
    return tmp_path


def test_burst_continue_no_server_crash(api_tmp: Path) -> None:
    """并发连点：不得 500；在任务仍存活时应出现 409。"""
    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = api_tmp
        web_server._active_project_id = None
        _reset_task_manager()
        _seed_ready(api_tmp)
        client = TestClient(web_app)
        codes: list[int] = []

        def _post():
            r = client.post(
                "/api/novel/continue",
                json={"dry_run": True, "autopilot": True, "max_chapters": 0, "force_resume": True},
            )
            return r.status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_post) for _ in range(8)]
            for fut in as_completed(futs):
                codes.append(fut.result())

        assert all(c in (200, 409) for c in codes)
        assert codes.count(200) >= 1
        assert codes.count(500) == 0
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base


def test_pipeline_alerts_scan_150_mixed_checkpoints(api_tmp: Path) -> None:
    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = api_tmp
        web_server._active_project_id = None
        _reset_task_manager()
        chapters = api_tmp / "workspace" / "chapters"
        chapters.mkdir(parents=True, exist_ok=True)
        for i in range(1, 151):
            d = chapters / f"chapter_{i:03d}"
            d.mkdir(exist_ok=True)
            if i % 7 == 0:
                (d / "checkpoint.json").write_text("{bad", encoding="utf-8")
            elif i % 3 == 0:
                (d / "checkpoint.json").write_text(
                    json.dumps(
                        {
                            "chapter_id": f"{i:03d}",
                            "last_stage": "quality_blocked",
                            "completed_stages": ["generation"],
                        }
                    ),
                    encoding="utf-8",
                )
            else:
                (d / "checkpoint.json").write_text(
                    json.dumps({"chapter_id": f"{i:03d}", "last_stage": "post_audit"}),
                    encoding="utf-8",
                )
        client = TestClient(web_app)
        t0 = time.perf_counter()
        resp = client.get("/api/pipeline-alerts")
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        alerts = resp.json().get("alerts") or []
        assert 40 <= len(alerts) <= 55
        assert elapsed < 3.0, f"扫描 150 章耗时 {elapsed:.2f}s，可能需优化"
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base


def test_dismiss_storm_on_same_chapter(api_tmp: Path) -> None:
    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = api_tmp
        web_server._active_project_id = None
        _reset_task_manager()
        d = api_tmp / "workspace" / "chapters" / "chapter_042"
        d.mkdir(parents=True, exist_ok=True)
        (d / "checkpoint.json").write_text(
            json.dumps({"chapter_id": "042", "last_stage": "quality_blocked"}),
            encoding="utf-8",
        )
        client = TestClient(web_app)
        for _ in range(5):
            r = client.post("/api/pipeline-alerts/042/dismiss")
            assert r.status_code == 200
        cp = json.loads((d / "checkpoint.json").read_text(encoding="utf-8"))
        assert cp.get("resolved_at")
    finally:
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base


# --- 3. 编排层：连续失败 → 熔断 ---


@pytest.mark.asyncio
async def test_briefs_pause_after_first_exception_skip(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    llm = StaticLLM({})
    config = PipelineConfig(root_dir=tmp_path, llm=llm)
    orch = NovelOrchestrator(config)
    orch.chapter_planner = MagicMock()
    orch.chapter_planner.aexpand = AsyncMock(
        return_value={"detailed_synopsis": "synopsis"}
    )
    orch.arun_chapter = AsyncMock(side_effect=RuntimeError("LLM exploded"))

    briefs = [{"chapter_id": f"{i:03d}", "goal": "g"} for i in range(1, 6)]

    results, stopped = await orch._run_chapter_briefs(briefs, arc_id="A01")
    assert stopped is True
    from novel_agent.services.arc_queue import load_arc_progress

    progress = load_arc_progress(tmp_path)
    assert progress.get("status") == "paused"
    assert progress.get("pause_reason") == "batch_skip_limit"
    assert len(results) == 0
    pending = list_pending_retries(tmp_path)
    assert any(p["chapter_id"] == "001" for p in pending)


@pytest.mark.asyncio
async def test_briefs_pause_immediately_on_quality_failure(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    llm = StaticLLM({})
    config = PipelineConfig(root_dir=tmp_path, llm=llm)
    orch = NovelOrchestrator(config)
    orch.chapter_planner = MagicMock()
    orch.chapter_planner.aexpand = AsyncMock(return_value={"detailed_synopsis": "x"})

    async def _fail_chapter(chapter_id: str, goal: str):
        return ChapterResult(
            chapter_id=chapter_id,
            final_path=tmp_path / "x.txt",
            audit={},
            warnings=["质量门禁未通过"],
        )

    orch.arun_chapter = _fail_chapter
    briefs = [{"chapter_id": f"{i:03d}", "goal": "g"} for i in range(1, 6)]

    results, stopped = await orch._run_chapter_briefs(briefs, arc_id="A01")
    assert stopped
    from novel_agent.services.arc_queue import load_arc_progress

    progress = load_arc_progress(tmp_path)
    assert progress.get("status") == "paused"
    assert progress.get("pause_reason") == "quality_blocked"
    assert len(results) == 1


# --- 4. TaskManager ---


@pytest.mark.asyncio
async def test_duplicate_chapter_submit_rejected(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    tm = TaskManager(tmp_path, max_concurrent=2)
    tid1 = await tm.submit_chapter("099", "goal-a", dry_run=True)
    assert tid1
    with pytest.raises(ValueError, match="already running"):
        await tm.submit_chapter("099", "goal-b", dry_run=True)
    await tm.abort_task(tid1)


@pytest.mark.asyncio
async def test_novel_continue_rejects_second_submit(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    tm = TaskManager(tmp_path, max_concurrent=2)
    tid1 = await tm.submit_novel_continue(
        dry_run=True, autopilot=True, max_chapters=0, max_rounds=1
    )
    assert tid1.startswith("novel-auto")
    with pytest.raises(ValueError, match="already running"):
        await tm.submit_novel_continue(
            dry_run=True, autopilot=True, max_chapters=0, max_rounds=1
        )
    t = tm._running_tasks.get(tid1)
    if t and not t.done():
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_circuit_paused_blocks_validate_without_force(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    (tmp_path / "config" / "pipeline.yaml").write_text(
        (tmp_path / "config" / "pipeline.yaml").read_text(encoding="utf-8")
        + "\n",
        encoding="utf-8",
    )
    record_novel_batch_paused(
        tmp_path,
        reason="circuit_breaker",
        last_chapter="005",
        arc_id="A01",
        streak=3,
    )
    ok, detail = validate_novel_continue(tmp_path, force_resume=False)
    assert not ok
    assert "熔断" in detail