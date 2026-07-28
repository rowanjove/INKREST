"""Novel autopilot helpers and round loop."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from novel_agent.services.arc_queue import record_novel_batch_paused, save_arc_progress
from novel_agent.services.novel_autopilot import (
    chapters_remaining_to_target,
    is_batch_circuit_paused,
    run_novel_autopilot,
)


def _outline(root: Path, target: int) -> None:
    (root / "workspace").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "target_chapters": target,
                "scale_profile": {"scale": "medium", "max_chapters": target},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_autopilot_stops_on_circuit_breaker(tmp_path: Path) -> None:
    _outline(tmp_path, 20)
    save_arc_progress(tmp_path, {"status": "running", "completed_chapters": 0})
    record_novel_batch_paused(
        tmp_path, reason="circuit_breaker", last_chapter="005", streak=5
    )

    orch = MagicMock()
    orch.root_dir = tmp_path
    orch._chapter_pipeline_complete = lambda cid: True
    orch.arun_arcs = AsyncMock(return_value=[])

    outcome = await run_novel_autopilot(orch, max_chapters=10, chapters_per_round=3)
    assert outcome.paused
    assert outcome.stopped_reason == "circuit_breaker"
    assert outcome.chapters_completed == 0
    orch.arun_arcs.assert_not_called()


@pytest.mark.asyncio
async def test_autopilot_runs_rounds_until_idle(tmp_path: Path, monkeypatch) -> None:
    _outline(tmp_path, 2)
    save_arc_progress(tmp_path, {"status": "running", "completed_chapters": 0})

    orch = MagicMock()
    orch.root_dir = tmp_path
    orch._chapter_pipeline_complete = lambda cid: True
    completed = {"n": 0}

    async def fake_arcs(**kwargs):
        if completed["n"] >= 2:
            return []
        completed["n"] += 2
        return [MagicMock(chapter_id="001"), MagicMock(chapter_id="002")]

    orch.arun_arcs = fake_arcs

    def remaining(_root: Path) -> int:
        return max(0, 2 - completed["n"])

    monkeypatch.setattr(
        "novel_agent.services.novel_autopilot.chapters_remaining_to_target",
        remaining,
    )
    monkeypatch.setattr(
        "novel_agent.services.novel_autopilot.has_more_batch_work",
        lambda _r, _fn: remaining(_r) > 0,
    )

    outcome = await run_novel_autopilot(
        orch, max_chapters=0, chapters_per_round=5, full_book=True, max_rounds=5
    )
    assert outcome.chapters_completed == 2
    assert outcome.rounds == 1
    assert outcome.stopped_reason == "target_reached"


def test_chapters_remaining_to_target(tmp_path: Path) -> None:
    _outline(tmp_path, 15)
    assert chapters_remaining_to_target(tmp_path) == 15


def test_chapters_remaining_uses_indexed_chapter_count(tmp_path: Path) -> None:
    from novel_agent.state.sqlite_store import SQLiteStateStore

    _outline(tmp_path, 5)
    store = SQLiteStateStore(tmp_path)
    for i in range(1, 5):
        chapter_id = f"{i:03d}"
        store.index_chapter(
            chapter_id,
            f"Chapter {chapter_id}",
            Path(f"workspace/chapters/chapter_{chapter_id}/chapter_final.txt"),
            1000,
            "low",
        )
    save_arc_progress(tmp_path, {"status": "running", "completed_chapters": 0})

    assert chapters_remaining_to_target(tmp_path) == 1


def test_is_batch_circuit_paused(tmp_path: Path) -> None:
    record_novel_batch_paused(tmp_path, reason="circuit_breaker", streak=3)
    assert is_batch_circuit_paused(tmp_path) is True
