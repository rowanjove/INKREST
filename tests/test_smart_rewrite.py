import json
import unittest
from pathlib import Path
import tempfile
import shutil
import dataclasses
from unittest.mock import MagicMock

from novel_agent.phases.base import ChapterContext
from novel_agent.phases.audit import AuditPhase
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig

class SmartRewriteTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-rewrite-test-"))
        
    def tearDown(self):
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_sync_smart_rewrite_refines_only_target_paragraph(self):
        # 1. 构造三段正文
        p1 = "阿强独自走在空旷的荒野上。微风吹过，拂起他的衣角。"
        p2 = "看到前方的野狼，他的心中不禁涌起了一股强烈的愤怒，整个人都震惊了。" # 违规段落，包含“不禁”、“愤怒”、“震惊”
        p3 = "他拔出腰间的长剑，目光变得坚定起来。"
        final_text = f"{p1}\n\n{p2}\n\n{p3}"
        
        # 2. 构造文本级问题
        issues = [{
            "type": "ai_flavor",
            "issue_layer": "text",
            "severity": "medium",
            "text": "情绪直写：愤怒、震惊",
            "target_text": "他的心中不禁涌起了一股强烈的愤怒，整个人都震惊了。",
            "why": "情绪直写违规",
            "fix": "通过肢体动作表现情绪"
        }]
        
        # 3. 设置 mock
        style_editor = MagicMock()
        # 让 style_editor 的 edit 返回修改后的新段落
        new_p2 = "看到前方的野狼，他攥紧了拳头，骨节微微发白，胸膛剧烈起伏着。"
        style_editor.edit.return_value = new_p2
        
        # 4. 初始化 orchestrator 和 config
        orchestrator = MagicMock()
        orchestrator.style_editor = style_editor
        orchestrator.planner.create_plan.return_value = {}
        orchestrator.length_fix.adjust = lambda text, range_: text
        orchestrator.continuity_checker.check.return_value = {"pass": True}
        orchestrator.auditor.audit.return_value = {"risk_level": "低", "issues": []}
        
        config = MagicMock()
        config.max_rewrites = 1
        
        audit_phase = AuditPhase(orchestrator)
        audit_phase.config = config
        
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="走出荒野",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir,
            reports_dir=self.tmpdir,
            plan={}
        )
        
        # 5. 执行同步局部重写
        res_text, res_audit, res_ctx = audit_phase._rewrite_iteration(
            ctx, final_text, plan_issues=[], issues=issues, state_text="", attempt=0
        )
        
        # 6. 断言 style_editor.edit 被调用了，且传入的 prompt 包含 p2 的内容
        style_editor.edit.assert_called_once()
        called_prompt = style_editor.edit.call_args[0][0]
        self.assertIn("待修改段落", called_prompt)
        self.assertIn(p2, called_prompt)
        # 并且包含了 p1 和 p3 做上下文参考
        self.assertIn(p1, called_prompt)
        self.assertIn(p3, called_prompt)
        
        # 7. 断言正文中只有 p2 被局部替换，而 p1 和 p3 维持原样
        paragraphs = res_text.split("\n\n")
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], p1)
        self.assertEqual(paragraphs[1], new_p2)
        self.assertEqual(paragraphs[2], p3)

    async def _async_smart_rewrite_test(self):
        p1 = "阿强独自走在空旷的荒野上。微风吹过，拂起他的衣角。"
        p2 = "看到前方的野狼，他的心中不禁涌起了一股强烈的愤怒，整个人都震惊了。"
        p3 = "他拔出腰间的长剑，目光变得坚定起来。"
        final_text = f"{p1}\n\n{p2}\n\n{p3}"
        
        issues = [{
            "type": "ai_flavor",
            "issue_layer": "text",
            "severity": "medium",
            "text": "情绪直写",
            "target_text": "他的心中不禁",
            "why": "情绪直写",
            "fix": "通过肢体动作表现"
        }]
        
        style_editor = MagicMock()
        new_p2 = "看到前方的野狼，他攥紧了拳头。"
        
        # Mock 异步方法
        async def mock_aedit(prompt):
            return new_p2
        style_editor.aedit = mock_aedit
        
        orchestrator = MagicMock()
        orchestrator.style_editor = style_editor
        orchestrator.planner.acreate_plan.return_value = {}
        orchestrator.length_fix.aadjust.return_value = final_text
        
        async def mock_aadjust(text, target):
            return text
        orchestrator.length_fix.aadjust = mock_aadjust
        
        async def mock_acheck(text, state):
            return {"pass": True}
        orchestrator.continuity_checker.acheck = mock_acheck
        
        async def mock_aaudit(text):
            return {"risk_level": "低", "issues": []}
        orchestrator.auditor.aaudit = mock_aaudit
        
        config = MagicMock()
        audit_phase = AuditPhase(orchestrator)
        audit_phase.config = config
        
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="走出荒野",
            chapter_dir=self.tmpdir,
            scenes_dir=self.tmpdir,
            reports_dir=self.tmpdir,
            plan={}
        )
        
        res_text, res_audit, res_ctx = await audit_phase._arewrite_iteration(
            ctx, final_text, plan_issues=[], issues=issues, state_text="", attempt=0
        )
        
        paragraphs = res_text.split("\n\n")
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], p1)
        self.assertEqual(paragraphs[1], new_p2)
        self.assertEqual(paragraphs[2], p3)

    def test_async_smart_rewrite_refines_only_target_paragraph(self):
        import asyncio
        # Use asyncio run helper
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(asyncio.run, self._async_smart_rewrite_test()).result()
        else:
            asyncio.run(self._async_smart_rewrite_test())
