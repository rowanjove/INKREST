import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.services.assistant_snapshot import (
    enrich_task_summaries,
    load_work_snapshot,
    summarize_unified_gate,
)


class AssistantSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="assistant-snapshot-"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir)

    def test_load_work_snapshot_from_outline_and_meta(self):
        (self.tmpdir / "workspace").mkdir(parents=True)
        (self.tmpdir / "config").mkdir(parents=True)
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps(
                {
                    "target_chapters": 200,
                    "scale_profile": {"scale": "long", "label": "长篇", "target_chapters": 200},
                    "macro_outline": [{"arc_id": "A01", "name": "卷一"}],
                }
            ),
            encoding="utf-8",
        )
        snap = load_work_snapshot(self.tmpdir)
        self.assertEqual(snap["scale"], "long")
        self.assertEqual(snap["target_chapters"], 200)
        self.assertTrue(snap["has_macro_outline"])

    def test_summarize_unified_gate_failed(self):
        reports = self.tmpdir / "workspace" / "chapters" / "chapter_002" / "reports"
        reports.mkdir(parents=True)
        (reports / "unified_gate.json").write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "quality": {
                        "guard_status": "fail",
                        "blocked_by": ["word_count", "pacing"],
                    },
                    "audit": {"risk_level": "medium", "issue_count": 3},
                }
            ),
            encoding="utf-8",
        )
        summary = summarize_unified_gate(self.tmpdir, "002")
        self.assertIsNotNone(summary)
        self.assertIn("未通过", summary)
        self.assertIn("word_count", summary)

    def test_enrich_task_summaries_adds_gate(self):
        reports = self.tmpdir / "workspace" / "chapters" / "chapter_001" / "reports"
        reports.mkdir(parents=True)
        (reports / "unified_gate.json").write_text(
            json.dumps({"overall_pass": True, "quality": {"overall_score": 0.9}}),
            encoding="utf-8",
        )
        tasks = [{"id": "t1", "chapter_id": "001", "status": "failed", "error": "gate"}]
        out = enrich_task_summaries(self.tmpdir, tasks)
        self.assertIn("gate_summary", out[0])
        self.assertIn("已通过", out[0]["gate_summary"])


if __name__ == "__main__":
    unittest.main()