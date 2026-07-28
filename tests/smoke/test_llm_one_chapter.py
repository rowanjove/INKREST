"""Optional real-LLM smoke (skipped unless NOVEL_AGENT_LLM_SMOKE=1)."""

import os
import tempfile
import unittest
from pathlib import Path

import pytest

from tests.helpers.seed_engine import seed_usable_daily_model


@pytest.mark.skipif(
    os.environ.get("NOVEL_AGENT_LLM_SMOKE", "").lower() not in ("1", "true", "yes"),
    reason="Set NOVEL_AGENT_LLM_SMOKE=1 and NOVEL_AGENT_SMOKE_MODEL to run",
)
class LlmOneChapterSmoke(unittest.TestCase):
    def test_one_chapter_generates_text(self):
        model_id = os.environ.get("NOVEL_AGENT_SMOKE_MODEL", "").strip()
        if not model_id:
            self.skipTest("NOVEL_AGENT_SMOKE_MODEL not set")

        tmp = Path(tempfile.mkdtemp(prefix="novel-llm-smoke-"))
        try:
            (tmp / "config").mkdir()
            (tmp / "config" / "pipeline.yaml").write_text(
                f"llm:\n  daily_model_id: {model_id}\nruntime:\n  max_workers: 1\n",
                encoding="utf-8",
            )
            seed_usable_daily_model(tmp, model_id=model_id)
            for d in ("assets", "workspace/chapters/chapter_001", "prompts", "state"):
                (tmp / d).mkdir(parents=True, exist_ok=True)
            (tmp / "assets" / "world_bible.md").write_text("x" * 40, encoding="utf-8")
            (tmp / "assets" / "style_guide.md").write_text("x" * 40, encoding="utf-8")
            (tmp / "assets" / "rules.md").write_text("x" * 40, encoding="utf-8")
            (tmp / "assets" / "sensitive_words.md").write_text("x" * 40, encoding="utf-8")

            from novel_agent.orchestrator import NovelOrchestrator
            from novel_agent.pipeline import PipelineConfig

            config = PipelineConfig.from_config(tmp)
            orch = NovelOrchestrator(config)
            result = orch.run_chapter("001", "主角登场，建立世界观。")
            text = (tmp / "workspace" / "chapters" / "chapter_001" / "final.txt").read_text(
                encoding="utf-8"
            )
            self.assertTrue(len(text) > 200, f"chapter too short: {len(text)}")
            self.assertEqual(result.chapter_id, "001")
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)