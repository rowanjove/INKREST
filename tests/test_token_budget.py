import unittest
import tempfile
import shutil
from pathlib import Path
from novel_agent.phases.base import ChapterContext
from novel_agent.phases.generation import GenerationPhase
from novel_agent.pipeline import PipelineConfig
from novel_agent.orchestrator import NovelOrchestrator

class TestTokenBudget(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-budget-test-"))
        self.config = PipelineConfig.dry_run(self.tmpdir)
        self.orchestrator = NovelOrchestrator(self.config)
        self.generation_phase = GenerationPhase(self.orchestrator)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_smart_downgrade_when_exceeding_budget(self):
        # 1. 验证 max_tokens_per_chapter 置低时（比如 5000），预估值（默认 1500+800 * 12 大于 20000）会触发降级
        self.orchestrator.config.max_tokens_per_chapter = 5000
        
        # 执行估算
        self.orchestrator._estimate_and_budget_chapter("001")
        
        # 应触发降级
        self.assertTrue(self.orchestrator.config.skip_style_edit)

        # 2. 验证当 skip_style_edit 为 True 时，会跳过 style editor
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="测试降级",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir / "scenes",
            reports_dir=self.tmpdir / "reports",
            plan={"scenes": [{"scene_id": "001-01"}]}
        )
        
        # 如果调用 _run_style_edit
        stitched = "Stitched text content."
        final_text, res_ctx = self.generation_phase._run_style_edit(ctx, stitched, "Raw text")
        
        # 结果应与 stitched 一致，不需要去调用 style_editor
        self.assertEqual(final_text, stitched)

    def test_cost_persisting_and_clearing(self):
        # 3. 验证 _persist_llm_cost 的落库和 call_log 清空
        client = self.orchestrator.config.llm
        client.call_log = [
            {
                "role": "writer",
                "model": "deepseek-chat",
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "latency_ms": 200,
                "timestamp": 1234567.0
            }
        ]
        
        # 持久化
        self.orchestrator._persist_llm_cost("001")
        
        # 验证 SQLite 内存在记录
        import sqlite3
        with sqlite3.connect(self.orchestrator.store.db_path) as conn:
            row = conn.execute("select count(*) from llm_cost_log").fetchone()
            self.assertEqual(row[0], 1)
        
        # 验证 call_log 已被清空
        self.assertEqual(len(client.call_log), 0)

if __name__ == "__main__":
    unittest.main()
