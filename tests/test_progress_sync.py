from pathlib import Path

from novel_agent.services.arc_queue import load_arc_progress
from novel_agent.services.progress_sync import (
    record_chapter_success,
    reconcile_progress_ledger,
)
from tests.test_full_chain_chaos import _seed_ready


def test_record_chapter_success_ledger(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    record_chapter_success(tmp_path, "001", pipeline_complete=True)
    record_chapter_success(tmp_path, "001", pipeline_complete=True)
    record_chapter_success(tmp_path, "002", pipeline_complete=True)
    prog = load_arc_progress(tmp_path)
    assert prog["completed_chapters"] == 2
    assert set(prog.get("completed_chapter_ids") or []) == {"001", "002"}


def test_reconcile_from_checkpoint(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    d = tmp_path / "workspace" / "chapters" / "chapter_003"
    d.mkdir(parents=True)
    (d / "checkpoint.json").write_text(
        '{"chapter_id":"003","completed_stages":["post_audit"]}',
        encoding="utf-8",
    )
    reconcile_progress_ledger(tmp_path)
    prog = load_arc_progress(tmp_path)
    assert prog["completed_chapters"] >= 1
    assert "003" in (prog.get("completed_chapter_ids") or [])