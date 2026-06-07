"""Mocked autopilot one-round smoke: task completes and writes autopilot_rounds.jsonl."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from novel_agent.services.novel_autopilot import AutopilotResult, run_novel_autopilot
from tests.test_full_chain_chaos import _seed_ready
from web.tasks import TaskManager


@pytest.mark.asyncio
async def test_autopilot_one_round_mock_writes_jsonl(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    tm = TaskManager(tmp_path, max_concurrent=2)

    async def fake_autopilot(orch, **kwargs):
        summary = {
            "round": 1,
            "chapters": 1,
            "last_id": "001",
            "tokens_used": 4200,
            "stopped_reason": "chapter_cap",
        }
        path = tmp_path / "workspace" / "autopilot_rounds.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**summary, "ts": "2026-06-06T12:00:00"}) + "\n", encoding="utf-8")
        return AutopilotResult(
            rounds=1,
            chapters_completed=1,
            stopped_reason="chapter_cap",
            round_summaries=[summary],
        )

    original = run_novel_autopilot
    import novel_agent.services.novel_autopilot as autopilot_mod

    autopilot_mod.run_novel_autopilot = fake_autopilot
    try:
        tid = await tm.submit_novel_continue(
            dry_run=True,
            autopilot=True,
            max_chapters=1,
            max_rounds=1,
        )
        task = tm._running_tasks[tid]
        await asyncio.wait_for(task, timeout=30)
        row = tm.store.get_task(tid)
        assert row is not None
        assert row.get("status") == "completed"
        result = row.get("result") or {}
        if isinstance(result, str):
            result = json.loads(result or "{}")
        assert result.get("autopilot") is True
        assert result.get("rounds") == 1
        assert result.get("chapters_completed") == 1

        log_path = tmp_path / "workspace" / "autopilot_rounds.jsonl"
        assert log_path.is_file()
        logged = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert logged.get("round") == 1
        assert logged.get("tokens_used") == 4200
    finally:
        autopilot_mod.run_novel_autopilot = original


@pytest.mark.asyncio
async def test_autopilot_one_round_records_tokens_via_persist_llm_cost(
    tmp_path: Path,
) -> None:
    """Integration smoke: real run_novel_autopilot + _persist_llm_cost token path."""
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.services.arc_queue import save_arc_progress

    _seed_ready(tmp_path)
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "target_chapters": 5,
                "scale_profile": {"scale": "medium", "max_chapters": 5},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    save_arc_progress(tmp_path, {"status": "running", "completed_chapters": 0})

    class _FakeLLM:
        def __init__(self) -> None:
            self.call_log = [
                {
                    "model": "deepseek-chat",
                    "prompt_tokens": 800,
                    "completion_tokens": 200,
                    "total_tokens": 1000,
                }
            ]

    orch = NovelOrchestrator(PipelineConfig.dry_run(tmp_path))

    async def fake_arcs(**kwargs):
        orch.config.llm_registry["writer"] = _FakeLLM()
        orch._persist_llm_cost("001")
        return [MagicMock(chapter_id="001")]

    orch.arun_arcs = fake_arcs

    outcome = await run_novel_autopilot(
        orch,
        max_chapters=1,
        chapters_per_round=1,
        full_book=True,
        max_rounds=1,
    )
    assert outcome.chapters_completed == 1
    assert outcome.round_summaries[0].get("tokens_used") == 1000

    log_path = tmp_path / "workspace" / "autopilot_rounds.jsonl"
    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged.get("tokens_used") == 1000
    assert logged.get("chapters") == 1


@pytest.mark.asyncio
async def test_autopilot_round_clears_stale_call_log_before_counting(
    tmp_path: Path,
) -> None:
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.services.arc_queue import save_arc_progress

    _seed_ready(tmp_path)
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps({"target_chapters": 3, "scale_profile": {"max_chapters": 3}}),
        encoding="utf-8",
    )
    save_arc_progress(tmp_path, {"status": "running", "completed_chapters": 0})

    class _FakeLLM:
        def __init__(self, logs):
            self.call_log = list(logs)

    fresh_llm = _FakeLLM(
        [{"model": "x", "prompt_tokens": 300, "completion_tokens": 100, "total_tokens": 400}]
    )

    orch = NovelOrchestrator(PipelineConfig.dry_run(tmp_path))
    # Stale logs from a prior failed chapter must not survive round reset.
    orch.config.llm_registry["writer"] = _FakeLLM(
        [{"model": "x", "prompt_tokens": 500, "completion_tokens": 0, "total_tokens": 500}]
    )

    async def fake_arcs(**kwargs):
        orch.config.llm_registry["writer"] = fresh_llm
        orch._persist_llm_cost("002")
        return [MagicMock(chapter_id="002")]

    orch.arun_arcs = fake_arcs

    outcome = await run_novel_autopilot(
        orch, max_chapters=1, chapters_per_round=1, full_book=True, max_rounds=1
    )
    assert outcome.round_summaries[0].get("tokens_used") == 400


def test_orchestrator_round_token_accumulator(tmp_path: Path) -> None:
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.pipeline import PipelineConfig

    _seed_ready(tmp_path)

    class _FakeLLM:
        def __init__(self) -> None:
            self.call_log = [
                {"model": "stub", "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            ]

    orch = NovelOrchestrator(PipelineConfig.dry_run(tmp_path))
    orch.config.llm_registry["writer"] = _FakeLLM()
    assert len(orch.config.get_call_log()) == 1
    orch.reset_round_token_accumulator()
    assert orch.config.get_call_log() == []
    orch._round_tokens_acc = 9000
    assert orch.consume_round_tokens() == 9000
    assert orch.consume_round_tokens() == 0