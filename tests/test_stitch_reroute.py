import unittest
import tempfile
import shutil
import dataclasses
from pathlib import Path
from novel_agent.phases.base import ChapterContext
from novel_agent.phases.generation import GenerationPhase
from novel_agent.phases.audit import AuditPhase
from novel_agent.pipeline import PipelineConfig
from novel_agent.orchestrator import NovelOrchestrator

class TestStitchReroute(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-stitch-test-"))
        self.config = PipelineConfig.dry_run(self.tmpdir)
        self.orchestrator = NovelOrchestrator(self.config)
        self.generation_phase = GenerationPhase(self.orchestrator)
        self.audit_phase = AuditPhase(self.orchestrator)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_skip_stitch_with_one_scene(self):
        # 1. 即使没有配置 skip_stitch，但只有一个场景时也应该跳过 Stitching
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="测试单场景",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir / "scenes",
            reports_dir=self.tmpdir / "reports",
            plan={"scenes": [{"scene_id": "001-01", "target_chars": [10, 20]}]}
        )
        ctx.scenes_dir.mkdir(parents=True, exist_ok=True)
        (ctx.scenes_dir / "scene_001-01.txt").write_text("场景一正文", encoding="utf-8")
        
        raw_text = "场景一正文"
        stitched, res_ctx = self.generation_phase._run_stitch(ctx, raw_text)
        self.assertEqual(stitched, raw_text)  # 应直接返回

    def test_skip_stitch_with_config(self):
        # 2. 配置了 skip_stitch 时，多个场景也跳过 Stitching
        self.orchestrator.config.skip_stitch = True
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="测试跳过",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir / "scenes",
            reports_dir=self.tmpdir / "reports",
            plan={"scenes": [
                {"scene_id": "001-01", "target_chars": [10, 20]},
                {"scene_id": "001-02", "target_chars": [10, 20]}
            ]}
        )
        ctx.scenes_dir.mkdir(parents=True, exist_ok=True)
        (ctx.scenes_dir / "scene_001-01.txt").write_text("正文一", encoding="utf-8")
        (ctx.scenes_dir / "scene_001-02.txt").write_text("正文二", encoding="utf-8")
        
        raw_text = "正文一\n\n正文二"
        stitched, res_ctx = self.generation_phase._run_stitch(ctx, raw_text)
        self.assertEqual(stitched, raw_text)  # 因为配置了 skip_stitch，直接返回 raw

    def test_rewrite_routing_to_stitch_editor(self):
        # 3. 验证当有接缝问题时重写路由指向 stitch_editor
        # 我们可以通过 mock auditor 输出的 issue，其中 why 包含 "场景接缝" 词汇
        # 确保它的重写调用了 stitch_editor.edit
        
        # 捕获 stitch_editor.edit 的调用次数
        original_edit = self.orchestrator.stitch_editor.edit
        call_count = 0
        def mock_edit(prompt):
            nonlocal call_count
            call_count += 1
            return "缝合后的段落"
        self.orchestrator.stitch_editor.edit = mock_edit

        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="测试路由",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir / "scenes",
            reports_dir=self.tmpdir / "reports",
            plan={"scenes": [{"scene_id": "001-01"}]},
            final_text="第一段\n\n第二段\n\n第三段"
        )
        ctx.scenes_dir.mkdir(parents=True, exist_ok=True)
        ctx.reports_dir.mkdir(parents=True, exist_ok=True)
        
        issues = [
            {"issue_layer": "text", "target_text": "第二段", "why": "场景接缝不够连贯", "fix": "进行重新缝合处理"}
        ]
        
        self.audit_phase._rewrite_iteration(ctx, ctx.final_text, [], issues, "{}", 0)
        self.assertEqual(call_count, 1)  # 验证了调用了 stitch_editor 修正！
        
        # 还原
        self.orchestrator.stitch_editor.edit = original_edit

if __name__ == "__main__":
    unittest.main()
