"""Chapter detail API: unified_gate, checkpoint, artifact_status."""

import json
import tempfile
import unittest
from pathlib import Path

import web.server as web_server


class ChapterDetailGateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-chapter-detail-"))
        self._orig_active = web_server._active_project_id
        self._orig_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None

    def tearDown(self):
        web_server._active_project_id = self._orig_active
        web_server.BASE_DIR = self._orig_base

    def _chapter_dir(self, chapter_id: str = "003"):
        d = self.tmpdir / "workspace" / "chapters" / f"chapter_{chapter_id}"
        (d / "reports").mkdir(parents=True, exist_ok=True)
        return d

    def test_get_chapter_includes_unified_gate_and_artifacts(self):
        chapter_dir = self._chapter_dir()
        chapter_dir.joinpath("plan.json").write_text(
            json.dumps({"chapter_title": "Gate Test"}), encoding="utf-8"
        )
        chapter_dir.joinpath("chapter_final.txt").write_text("正文。", encoding="utf-8")
        unified = {
            "blocked": True,
            "overall_pass": False,
            "resumable_from": "audit",
            "rewrite_hints": "- [门禁] 需改写",
            "quality": {"guard_status": "FAIL", "blocked_by": ["style"]},
            "audit": {"risk_level": "中", "requires_rewrite": False},
        }
        (chapter_dir / "reports" / "unified_gate.json").write_text(
            json.dumps(unified), encoding="utf-8"
        )
        (chapter_dir / "reports" / "quality.json").write_text(
            json.dumps({"overall_pass": False, "guard_summary": {"overall_status": "FAIL"}}),
            encoding="utf-8",
        )
        (chapter_dir / "reports" / "audit.json").write_text(
            json.dumps({"risk_level": "中"}), encoding="utf-8"
        )
        (chapter_dir / "checkpoint.json").write_text(
            json.dumps(
                {
                    "chapter_id": "003",
                    "completed_stages": ["planner", "generation"],
                    "last_stage": "quality_blocked",
                    "resumable_from": "audit",
                }
            ),
            encoding="utf-8",
        )
        (chapter_dir / "state_update.json").write_text(
            json.dumps({"events": [{"id": "e1"}]}), encoding="utf-8"
        )

        detail = web_server.get_chapter("003")

        self.assertTrue(detail.unified_gate.get("blocked"))
        self.assertEqual(detail.checkpoint.get("last_stage"), "quality_blocked")
        self.assertGreaterEqual(len(detail.artifact_status), 5)

        by_key = {row["key"]: row for row in detail.artifact_status}
        self.assertEqual(by_key["unified_gate"]["status"], "authoritative")
        self.assertEqual(by_key["state_update"]["status"], "stale")
        self.assertEqual(by_key["audit"]["status"], "reference")
        self.assertEqual(by_key["final"]["status"], "authoritative")