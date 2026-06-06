"""Long-run scale: pagination, vector window, compress schedule, circuit breaker."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.control.long_run import (
    chapter_run_is_failure,
    resolve_audit_max_rewrites,
    resolve_batch_fail_streak_max,
    resolve_compress_schedule,
    resolve_vector_search_window,
)
from novel_agent.orchestrator import ChapterResult
from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.vector_store import metadata_in_chapter_window
import web.server as web_server


class LongRunScaleTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-longrun-"))
        (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "workspace").mkdir(parents=True, exist_ok=True)

    def test_epic_scale_disables_audit_rewrites_by_default(self):
        outline = {
            "scale_profile": {"scale": "epic", "planning_mode": "fractal_dynamic_volume"},
        }
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps(outline), encoding="utf-8"
        )
        self.assertEqual(resolve_audit_max_rewrites(self.tmpdir), 0)

    def test_compress_schedule_reads_scale_profile(self):
        outline = {
            "scale_profile": {
                "scale": "epic",
                "compress_hot_every": 12,
                "compress_warm_every": 60,
            },
        }
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps(outline), encoding="utf-8"
        )
        hot, warm, thresh = resolve_compress_schedule(self.tmpdir)
        self.assertEqual(hot, 12)
        self.assertEqual(warm, 60)
        self.assertGreaterEqual(thresh, 1)

    def test_chapter_index_sync_and_pagination(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            for cid in ("001", "002", "010"):
                d = self.tmpdir / "workspace" / "chapters" / f"chapter_{cid}"
                d.mkdir(parents=True)
                (d / "chapter_final.txt").write_text("字" * 10, encoding="utf-8")
                (d / "plan.json").write_text(
                    json.dumps({"chapter_title": f"Ch{cid}"}), encoding="utf-8"
                )
            store = SQLiteStateStore(self.tmpdir)
            self.assertEqual(sync_chapters_from_disk(self.tmpdir, store), 3)
            page = web_server.list_chapters(offset=0, limit=2, sync=False)
            self.assertEqual(page.total, 3)
            self.assertEqual(len(page.items), 2)
            self.assertEqual(page.items[0].chapter_id, "001")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_vector_chapter_window_filter(self):
        self.assertTrue(metadata_in_chapter_window({"chapter": "050"}, "100", 80))
        self.assertFalse(metadata_in_chapter_window({"chapter": "001"}, "100", 80))
        self.assertTrue(metadata_in_chapter_window({"chapter": "001"}, "100", 0))

    def test_chapter_run_is_failure_detects_quality_block(self):
        result = ChapterResult(
            chapter_id="003",
            final_path=Path("x"),
            audit={},
            warnings=["质量门禁未通过，已暂停落库"],
        )
        self.assertTrue(chapter_run_is_failure(result))

    def test_batch_fail_streak_from_pipeline(self):
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            "runtime:\n  batch_fail_streak_max: 3\n", encoding="utf-8"
        )
        self.assertEqual(resolve_batch_fail_streak_max(self.tmpdir), 3)
        self.assertEqual(resolve_vector_search_window(self.tmpdir), 80)