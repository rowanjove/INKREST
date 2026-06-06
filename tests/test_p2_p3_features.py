"""P2/P3 backlog: progress summary, external review, export trial, skip pause."""

import json
from pathlib import Path

import pytest

from novel_agent.control.long_run import resolve_batch_skip_pause_max
from novel_agent.services.external_review import (
    block_continue_until_external_pass,
    count_pending_external,
    list_pending_external,
    set_external_review_status,
)
from novel_agent.services.novel_run_guard import validate_novel_continue
from novel_agent.services.progress_summary import build_progress_summary
from tests.test_full_chain_chaos import _seed_ready


def test_progress_summary_authoritative(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    prog_path = tmp_path / "workspace" / "reports" / "novel_batch_progress.json"
    prog_path.parent.mkdir(parents=True, exist_ok=True)
    prog_path.write_text(
        json.dumps({"status": "running", "completed_chapters": 7}),
        encoding="utf-8",
    )
    summary = build_progress_summary(tmp_path)
    assert summary["authoritative_completed"] == 7
    assert "progress_note" in summary
    assert "pending_retry_count" in summary
    assert "pending_gate_count" in summary
    assert "remaining_chapters" in summary
    assert "last_chapter_id" in summary


def test_external_review_and_continue_block(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    cfg = tmp_path / "config" / "pipeline.yaml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8")
        + "\nruntime:\n  block_continue_until_external_pass: true\n",
        encoding="utf-8",
    )
    set_external_review_status(tmp_path, "002", "pending_external")
    assert len(list_pending_external(tmp_path)) == 1
    assert block_continue_until_external_pass(tmp_path)
    ok, msg = validate_novel_continue(tmp_path, force_resume=True)
    assert not ok
    assert "外审" in msg
    set_external_review_status(tmp_path, "002", "none")
    assert count_pending_external(tmp_path) == 0


def test_export_trial_requires_body(tmp_path: Path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    import web.context as web_context
    import web.server as web_server
    from web.server import app as web_app

    _seed_ready(tmp_path)
    d = tmp_path / "workspace" / "chapters" / "chapter_001"
    d.mkdir(parents=True)
    (d / "plan.json").write_text('{"chapter_title":"t"}', encoding="utf-8")
    (d / "chapter_final.txt").write_text("正文" * 20, encoding="utf-8")

    original_active = web_server._active_project_id
    original_base = web_server.BASE_DIR
    try:
        web_server.BASE_DIR = tmp_path
        web_server._active_project_id = None
        web_context._task_manager = None
        client = TestClient(web_app)
        r = client.post("/api/chapters/export-trial", json={"chapter_ids": ["001"]})
        assert r.status_code == 200
        assert r.json()["char_count"] > 0
        assert "001" in r.json()["chapter_ids"]
    finally:
        web_context._task_manager = None
        web_server._active_project_id = original_active
        web_server.BASE_DIR = original_base


def test_batch_skip_pause_max_default(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    assert resolve_batch_skip_pause_max(tmp_path) >= 0