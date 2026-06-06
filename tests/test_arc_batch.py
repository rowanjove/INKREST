"""Arc batch queue and progress."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.services.arc_queue import (
    clear_batch_pause_for_resume,
    load_arc_progress,
    load_workspace_arcs,
    mark_arc_progress,
    mark_novel_batch_finished,
    record_novel_batch_paused,
    save_arc_progress,
    select_arcs,
    should_run_by_arc_batches,
    sort_briefs_by_dependencies,
)


class ArcBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-arc-"))
        ws = self.tmpdir / "workspace"
        ws.mkdir(parents=True)
        (ws / "arc_A01.json").write_text(
            json.dumps(
                {
                    "arc_id": "A01",
                    "chapters": [{"chapter_id": "001"}, {"chapter_id": "002"}],
                }
            ),
            encoding="utf-8",
        )
        (ws / "arc_A02.json").write_text(
            json.dumps(
                {
                    "arc_id": "A02",
                    "chapters": [{"chapter_id": "003"}],
                }
            ),
            encoding="utf-8",
        )

    def test_load_workspace_arcs(self):
        arcs = load_workspace_arcs(self.tmpdir)
        self.assertEqual(len(arcs), 2)
        self.assertEqual(arcs[0]["arc_id"], "A01")

    def test_select_arcs_by_start(self):
        arcs = load_workspace_arcs(self.tmpdir)
        picked = select_arcs(arcs, start_arc_id="A02")
        self.assertEqual(len(picked), 1)
        self.assertEqual(picked[0]["arc_id"], "A02")

    def test_progress_roundtrip(self):
        save_arc_progress(self.tmpdir, {"status": "running", "last_arc_id": "A01"})
        prog = load_arc_progress(self.tmpdir)
        self.assertEqual(prog["last_arc_id"], "A01")

    def test_should_run_by_arc_batches(self):
        self.assertTrue(should_run_by_arc_batches(100, "medium"))
        self.assertTrue(should_run_by_arc_batches(20, "epic"))
        self.assertFalse(should_run_by_arc_batches(20, "short"))

    def test_sort_briefs_by_dependencies(self):
        briefs = [
            {"chapter_id": "003", "depends_on": ["002"]},
            {"chapter_id": "001"},
            {"chapter_id": "002", "depends_on": ["001"]},
        ]
        ordered = sort_briefs_by_dependencies(briefs)
        ids = [b["chapter_id"] for b in ordered]
        self.assertEqual(ids, ["001", "002", "003"])

    def test_clear_batch_pause_for_resume(self):
        record_novel_batch_paused(self.tmpdir, reason="circuit_breaker", streak=3)
        clear_batch_pause_for_resume(self.tmpdir)
        prog = load_arc_progress(self.tmpdir)
        self.assertEqual(prog["status"], "running")
        self.assertNotIn("pause_reason", prog)
        self.assertEqual(prog.get("fail_streak"), 0)

    def test_mark_arc_done_does_not_clear_global_paused(self):
        record_novel_batch_paused(self.tmpdir, reason="circuit_breaker")
        mark_arc_progress(self.tmpdir, "A01", "done", chapters_done=2)
        prog = load_arc_progress(self.tmpdir)
        self.assertEqual(prog["status"], "paused")
        self.assertEqual(prog["arcs"]["A01"]["status"], "done")

    def test_mark_novel_batch_finished(self):
        save_arc_progress(self.tmpdir, {"status": "running"})
        mark_novel_batch_finished(self.tmpdir)
        self.assertEqual(load_arc_progress(self.tmpdir)["status"], "done")