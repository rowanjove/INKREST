import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novel_agent.approval import ApprovalGate
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig


class CheckpointRollbackTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-checkpoint-test-"))
        self.config = PipelineConfig.dry_run(self.tmpdir)
        self.config.interactive = True
        self.orchestrator = NovelOrchestrator(self.config)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_approval_rejection_rolls_back_audit_checkpoint(self):
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("测试正文", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps({"chapter_id": "001", "chapter_title": "第一章", "scenes": []}),
            encoding="utf-8",
        )
        checkpoint = {
            "chapter_id": "001",
            "completed_stages": ["generation", "audit"],
            "last_stage": "audit",
        }
        (chapter_dir / "checkpoint.json").write_text(
            json.dumps(checkpoint, ensure_ascii=False),
            encoding="utf-8",
        )

        completed = list(checkpoint["completed_stages"])
        rolled = self.orchestrator._rollback_checkpoint_after_approval_rejection(
            chapter_dir, "001", completed
        )

        self.assertEqual(rolled, ["generation"])
        saved = json.loads((chapter_dir / "checkpoint.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["completed_stages"], ["generation"])
        self.assertEqual(saved["last_stage"], "approval_rejected")

    @patch.object(ApprovalGate, "request_approval", return_value=False)
    def test_post_audit_rejection_leaves_resumable_checkpoint(self, _mock_approval):
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_002"
        reports_dir = chapter_dir / "reports"
        reports_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("第二章正文", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps(
                {
                    "chapter_id": "002",
                    "chapter_title": "第二章",
                    "target_chars": [100, 500],
                    "scenes": [{"scene_id": "002-01", "target_chars": [100, 500]}],
                }
            ),
            encoding="utf-8",
        )
        (reports_dir / "audit.json").write_text(
            json.dumps({"risk_level": "低", "issues": []}),
            encoding="utf-8",
        )
        (chapter_dir / "state_update.json").write_text("{}", encoding="utf-8")
        (chapter_dir / "checkpoint.json").write_text(
            json.dumps(
                {"chapter_id": "002", "completed_stages": ["generation", "audit"]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        import asyncio

        result = asyncio.run(self.orchestrator.arun_chapter("002", "继续写第二章"))
        self.assertEqual(result.audit.get("risk_level"), "pending")

        saved = json.loads((chapter_dir / "checkpoint.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["completed_stages"], ["generation"])