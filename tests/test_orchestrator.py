import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from novel_agent.agents.base import StaticLLM
from novel_agent.agents.chapter_summary import ChapterSummaryAgent
from novel_agent.agents.continuity_checker import ContinuityCheckerAgent
from novel_agent.agents.asset_compressor import AssetCompressorAgent, compress_assets
from novel_agent.agents.length_fix import LengthFixAgent
from novel_agent.approval import ApprovalGate
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.state.sqlite_store import SQLiteStateStore


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-orchestrator-test-"))

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_chapter_summary_agent_returns_markdown_summary(self):
        llm = StaticLLM(
            {"chapter_summary": "## 章节概述\n事件推进。\n\n## 人物发展\n- 主角：更警惕。"}
        )
        agent = ChapterSummaryAgent(llm)
        summary = agent.summarize("正文")
        self.assertIn("## 章节概述", summary)
        self.assertIn("## 人物发展", summary)

    def test_length_fix_uses_expander_or_compressor_role(self):
        llm = StaticLLM({"expander": "扩写后文本", "compressor": "压缩后文本"})
        fixer = LengthFixAgent(llm)
        expanded = fixer.adjust("短", [10, 20])
        compressed = fixer.adjust("很长很长很长很长很长", [1, 3])
        self.assertEqual(expanded, "扩写后文本")
        self.assertEqual(compressed, "压缩后文本")

    def test_orchestrator_generates_chapter_workspace_and_reports(self):
        llm = StaticLLM(
            responses={
                "planner": json.dumps(
                    {
                        "chapter_id": "001",
                        "chapter_title": "雨夜来客",
                        "target_chars": [20, 80],
                        "scenes": [
                            {
                                "scene_id": "001-01",
                                "target_chars": [10, 60],
                                "purpose": "建立雨夜出租屋的压迫感",
                                "entry": "林澈回到出租屋",
                                "exit": "灯灭了",
                                "must_include": ["出租屋", "停电"],
                                "must_not_include": ["解释能力来源"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                "writer": "林澈推开出租屋的门，雨水顺着袖口滴在地上。灯闪了两下，彻底灭了。",
                "stitch_editor": "林澈推开出租屋的门，雨水顺着袖口滴在地上.灯闪了两下，彻底灭了。",
                "style_editor": "林澈推开出租屋那扇有些破旧的门，冰冷的雨水顺着袖口滴在地上。灯光无力地闪烁了两下，随后便彻底熄灭，将一切吞没在黑暗之中。",
                "continuity_checker": '{"pass":true,"issues":[]}',
                "auditor": json.dumps(
                    {
                        "risk_level": "低",
                        "issues": [],
                        "state_update": {
                            "events": [
                                {
                                    "id": "E001_001",
                                    "summary": "林澈回到出租屋后遭遇停电。",
                                }
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
                "chapter_summary": "## 章节概述\n林澈遭遇停电。\n\n## 人物发展\n- 林澈：更加警惕。",
            }
        )
        config = PipelineConfig(root_dir=self.tmpdir, llm=llm)
        orchestrator = NovelOrchestrator(config)
        result = orchestrator.run_chapter("001", "主角雨夜回到出租屋，并遭遇第一次异常。")

        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        self.assertTrue((chapter_dir / "plan.json").exists())
        self.assertTrue((chapter_dir / "scene_001-01_context.md").exists())
        self.assertTrue((chapter_dir / "scenes" / "scene_001-01.txt").exists())
        self.assertTrue((chapter_dir / "chapter_final.txt").exists())
        self.assertTrue((chapter_dir / "reports" / "wordcount.json").exists())
        self.assertTrue((chapter_dir / "reports" / "audit.json").exists())
        self.assertTrue((chapter_dir / "reports" / "continuity.json").exists())
        self.assertTrue((chapter_dir / "chapter_summary.md").exists())
        self.assertTrue((self.tmpdir / "dashboard" / "index.html").exists())
        self.assertTrue((self.tmpdir / "state" / "snapshots" / "chapter_001").exists())
        conn = sqlite3.connect(self.tmpdir / "data" / "novel.sqlite")
        try:
            row = conn.execute(
                "select final_path from chapters where id = ?", ("001",)
            ).fetchone()
            summary_row = conn.execute(
                "select summary from chapter_summaries where chapter_id = ?", ("001",)
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertIn("林澈遭遇停电", summary_row[0])
        self.assertEqual(result.chapter_id, "001")
        self.assertEqual(result.audit["risk_level"], "低")

    def test_context_builder_includes_relevant_history_from_sqlite(self):
        from novel_agent.state.vector_store import VectorChunk
        from novel_agent.agents.context_builder import ContextBuilderAgent
        cb = ContextBuilderAgent(self.tmpdir)
        cb.vector_store.upsert([
            VectorChunk(
                id="E012",
                type="event",
                text="黑色录音笔指向白塔医院。",
                metadata={"chapter": "012"}
            )
        ])
        context = cb.build(
            "调查白塔医院和黑色录音笔",
            {
                "scene_id": "013-01",
                "target_chars": [400, 600],
                "purpose": "延续白塔医院线索",
                "entry": "林澈拿出录音笔",
                "exit": "他决定出门",
                "must_include": ["白塔医院", "黑色录音笔"],
            },
        )
        self.assertIn("相关历史事件", context)
        self.assertIn("黑色录音笔指向白塔医院", context)

    def test_context_builder_includes_relevant_timeline_network(self):
        from novel_agent.state.vector_store import VectorChunk
        from novel_agent.agents.context_builder import ContextBuilderAgent
        cb = ContextBuilderAgent(self.tmpdir)
        cb.vector_store.upsert([
            VectorChunk(
                id="F001",
                type="timeline_node",
                text="白塔医院地下二层：建筑图纸里不存在的楼层。",
                metadata={"chapter": "012", "node_type": "setting"}
            )
        ])
        context = cb.build(
            "调查白塔医院",
            {
                "scene_id": "013-01",
                "target_chars": [400, 600],
                "purpose": "延续白塔医院线索",
                "entry": "林澈进入医院",
                "exit": "他找到电梯",
                "must_include": ["白塔医院"],
            },
        )
        self.assertIn("相关时间线网络", context)
        self.assertIn("白塔医院地下二层", context)

    def test_context_builder_includes_vector_recall_section(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent
        context = ContextBuilderAgent(self.tmpdir).build(
            "测试目标",
            {"scene_id": "001-01", "target_chars": [100, 200], "purpose": "测试"},
        )
        self.assertIn("语义相关片段", context)
        self.assertIn("暂无", context)  # StubVectorStore returns nothing

    def test_context_builder_omits_vector_recall_when_scale_disables_vectors(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        ws = self.tmpdir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "outline.json").write_text(
            json.dumps({"scale_profile": {"scale": "short", "vector_enabled": False}}),
            encoding="utf-8",
        )
        context = ContextBuilderAgent(self.tmpdir).build(
            "测试目标",
            {"scene_id": "001-01", "target_chars": [100, 200], "purpose": "测试"},
        )
        self.assertNotIn("语义相关片段", context)

    def test_query_duplicate_warnings_skipped_when_vector_disabled(self):
        llm = StaticLLM({})
        config = PipelineConfig(root_dir=self.tmpdir, llm=llm)
        orch = NovelOrchestrator(config)
        ws = self.tmpdir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "outline.json").write_text(
            json.dumps({"scale_profile": {"scale": "micro", "vector_enabled": False}}),
            encoding="utf-8",
        )
        self.assertEqual(orch.chapter_post._query_duplicate_warnings("001", "测试目标"), "")

    def test_continuity_checker_returns_structured_report(self):
        llm = StaticLLM({"continuity_checker": '{"pass": true, "issues": []}'})
        agent = ContinuityCheckerAgent(llm)
        report = agent.check("章节正文", "当前状态")
        self.assertTrue(report["pass"])
        self.assertEqual(report["issues"], [])

    def test_continuity_checker_handles_unparseable_output(self):
        llm = StaticLLM({"continuity_checker": "这不是JSON"})
        agent = ContinuityCheckerAgent(llm)
        report = agent.check("章节正文")
        self.assertFalse(report["pass"])
        self.assertEqual(report["issues"][0]["type"], "parse_error")

    def test_asset_compressor_returns_compression_result(self):
        llm = StaticLLM({
            "asset_compressor": json.dumps({
                "compressed": True,
                "archived_threads": [{"id": "T004", "title": "旧伏笔"}],
                "removed_events": ["E001"],
            }, ensure_ascii=False)
        })
        agent = AssetCompressorAgent(llm)
        result = agent.compress("状态汇总")
        self.assertTrue(result["compressed"])
        self.assertEqual(len(result["archived_threads"]), 1)

    def test_compress_assets_cli_merges_archived_threads(self):
        state_dir = self.tmpdir / "state"
        state_dir.mkdir()
        (state_dir / "events.yaml").write_text(
            "events:\n  - id: E001\n    summary: 旧事件\n  - id: E002\n    summary: 新事件\n",
            encoding="utf-8",
        )
        llm = StaticLLM({
            "asset_compressor": json.dumps({
                "compressed": True,
                "archived_threads": [{"id": "T001", "title": "已关闭伏笔"}],
                "removed_events": ["E001"],
            }, ensure_ascii=False)
        })
        result = compress_assets(self.tmpdir, llm)

        self.assertTrue(result["compressed"])
        archive_path = state_dir / "archive" / "closed_threads.yaml"
        self.assertTrue(archive_path.exists())
        events_text = (state_dir / "events.yaml").read_text(encoding="utf-8")
        self.assertNotIn("E001", events_text)
        self.assertIn("E002", events_text)

    def test_approval_gate_auto_passes_in_non_interactive(self):
        gate = ApprovalGate(interactive=False)
        self.assertTrue(gate.request_approval("001", self.tmpdir))

    def test_approval_gate_creates_instance_with_interactive_flag(self):
        gate = ApprovalGate(interactive=True)
        self.assertTrue(gate.interactive)

    def test_constraint_synthesizer_turns_secret_into_constraint(self):
        from novel_agent.control.constraint_synthesizer import synthesize_constraints
        state = {"secrets": [{"title": "真实身份", "status": "hidden", "description": "沈星璃不能知道父亲身份"}]}

        constraints = synthesize_constraints(state=state, recall_items=[], scene={})

        self.assertIn("不可提前揭露：真实身份", constraints[0])

    def test_context_builder_includes_synthesized_constraints(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_secret({
            "id": "SEC_001",
            "title": "真实身份",
            "status": "hidden",
            "description": "沈星璃不能知道父亲身份",
            "chapter_id": "001",
        })
        agent = ContextBuilderAgent(self.tmpdir)

        context = agent.build("测试目标", {"scene_id": "002-01", "purpose": "测试"})

        self.assertIn("本章硬约束", context)
        self.assertIn("不可提前揭露：真实身份", context)

    def test_context_builder_respects_budget(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        cfg_dir = self.tmpdir / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "pipeline.yaml").write_text(
            "chapter:\n  writer_anti_ai_hints: false\n", encoding="utf-8"
        )
        agent = ContextBuilderAgent(self.tmpdir, max_context_chars=200)
        context = agent.build(
            "测试目标",
            {"scene_id": "001-01", "target_chars": [100, 200], "purpose": "测试"},
        )
        self.assertLess(len(context), 500)

    def test_truncation_detection_identifies_truncated_output(self):
        from novel_agent.orchestrator import _detect_truncation
        self.assertTrue(_detect_truncation("a" * 200, ""))
        self.assertTrue(_detect_truncation("a" * 200, "a" * 50))
        self.assertFalse(_detect_truncation("a" * 200, "a" * 190 + "。"))
        self.assertFalse(_detect_truncation("short", "short"))

    def test_run_novel_generates_outline_and_chapters(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        orchestrator = NovelOrchestrator(config)
        results = orchestrator.run_novel(
            theme="测试主题",
            genre="玄幻",
            target_chapters=1,
        )
        self.assertTrue(len(results) >= 1)
        outline_path = self.tmpdir / "workspace" / "outline.json"
        self.assertTrue(outline_path.exists())
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        self.assertIn("macro_outline", outline)

    def test_chief_editor_returns_valid_outline(self):
        from novel_agent.agents.chief_editor import ChiefEditorAgent
        llm = StaticLLM({
            "chief_editor": json.dumps({
                "title_options": ["《测试小说》"],
                "logline": "一句话卖点",
                "core_theme": "冒险",
                "genre_positioning": "玄幻",
                "target_reader": "男频读者",
                "reader_promise": ["精彩打斗"],
                "world_rules": ["灵气为基础"],
                "protagonist": {"name": "林澈", "desire": "复仇", "flaw": "执着", "edge": "特殊体质", "limit": "每日一次"},
                "main_cast": [],
                "antagonistic_forces": ["白塔组织"],
                "macro_outline": [
                    {"arc_id": "A01", "name": "觉醒篇", "chapters": "1-10", "goal": "觉醒能力", "turning_point": "发现真相", "payoff": "初战告捷"}
                ],
                "forbidden_moves": ["开挂"]
            }, ensure_ascii=False)
        })
        agent = ChiefEditorAgent(llm)
        outline = agent.plan_novel("测试主题", "玄幻", 10)
        self.assertIn("macro_outline", outline)
        self.assertEqual(outline["protagonist"]["name"], "林澈")
        self.assertEqual(outline["title_options"][0], "《测试小说》")

    def test_chief_editor_fallback_on_parse_error(self):
        from novel_agent.agents.chief_editor import ChiefEditorAgent
        llm = StaticLLM({"chief_editor": "这不是JSON"})
        agent = ChiefEditorAgent(llm)
        outline = agent.plan_novel("测试", "玄幻", 5)
        self.assertIn("macro_outline", outline)
        self.assertIn("protagonist", outline)

    def test_managing_editor_splits_chapters(self):
        from novel_agent.agents.managing_editor import ManagingEditorAgent
        llm = StaticLLM({
            "managing_editor": json.dumps({
                "arc_id": "A01",
                "arc_name": "起始篇",
                "arc_goal": "觉醒",
                "chapters": [
                    {"chapter_id": "001", "chapter_title": "雨夜", "chapter_goal": "遭遇停电"},
                    {"chapter_id": "002", "chapter_title": "觉醒", "chapter_goal": "能力觉醒"},
                ]
            }, ensure_ascii=False)
        })
        agent = ManagingEditorAgent(llm)
        outline = {
            "protagonist": {"name": "主角"},
            "main_cast": [],
            "antagonistic_forces": [],
            "forbidden_moves": [],
            "macro_outline": [{"arc_id": "A01", "name": "起始篇", "chapters": "1-2", "goal": "觉醒"}],
        }
        result = agent.split_chapters(outline)
        self.assertEqual(len(result["chapters"]), 2)
        self.assertEqual(result["chapters"][0]["chapter_id"], "001")

    def test_chapter_planner_expands_brief(self):
        from novel_agent.agents.chapter_planner import ChapterPlannerAgent
        llm = StaticLLM({
            "chapter_planner": json.dumps({
                "chapter_id": "001",
                "chapter_title": "雨夜",
                "detailed_synopsis": "林澈在雨夜回到出租屋，遭遇停电，发现异常。",
                "beats": [
                    {"beat_id": "B01", "function": "开场", "content": "回到出租屋", "state_change": "正常"},
                    {"beat_id": "B02", "function": "冲突", "content": "停电", "state_change": "紧张"},
                ],
                "character_intents": [{"character": "林澈", "wants": "休息", "hidden_pressure": "", "change": "警觉"}],
                "foreshadow_plan": [],
                "handoff_to_scene_planner": {"must_include": ["停电"], "must_not_include": []}
            }, ensure_ascii=False)
        })
        agent = ChapterPlannerAgent(llm)
        brief = {"chapter_id": "001", "chapter_title": "雨夜", "chapter_goal": "遭遇停电"}
        result = agent.expand(brief)
        self.assertIn("detailed_synopsis", result)
        self.assertEqual(len(result["beats"]), 2)

    def test_state_extractor_returns_structured_state(self):
        from novel_agent.agents.state_extractor import StateExtractorAgent
        llm = StaticLLM({
            "state_extractor": json.dumps({
                "events": [{"id": "E001_001", "summary": "停电事件", "characters": ["林澈"], "objects": [], "threads": []}],
                "characters": {"林澈": {"location": "出租屋", "emotion": "警惕"}},
                "objects": [],
                "threads": [],
                "foreshadows": [],
                "hooks": []
            }, ensure_ascii=False)
        })
        agent = StateExtractorAgent(llm)
        result = agent.extract("林澈推开门，灯灭了。", "001")
        self.assertEqual(len(result["events"]), 1)
        self.assertIn("林澈", result["characters"])

    def test_state_extractor_handles_empty_text(self):
        from novel_agent.agents.state_extractor import StateExtractorAgent
        llm = StaticLLM({})
        agent = StateExtractorAgent(llm)
        result = agent.extract("", "001")
        self.assertEqual(result["events"], [])

    def test_planner_scene_defaults_include_anti_ai_controls(self):
        from novel_agent.agents.planner import PlannerAgent
        llm = StaticLLM({"planner": json.dumps({
            "chapter_id": "001",
            "chapter_title": "开播",
            "scenes": [{"scene_id": "001-01", "purpose": "主角第一次证明自己"}],
        }, ensure_ascii=False)})

        plan = PlannerAgent(llm).create_plan("001", "主角第一次证明自己")

        scene = plan["scenes"][0]
        self.assertIn(scene["scene_type"], {"setup", "build", "burst", "transition"})
        self.assertIn(scene["detail_level"], {"brief", "normal", "full", "skip"})
        self.assertIn("禁止直接写角色情绪", scene["must_not_include"])

    def test_auditor_augments_report_with_local_ai_flavor_check(self):
        from novel_agent.agents.auditor import AuditorAgent
        llm = StaticLLM({"auditor": json.dumps({
            "risk_level": "低",
            "issues": [],
            "state_update": {"events": []},
            "narrative_hooks": [],
        }, ensure_ascii=False)})

        report = AuditorAgent(llm).audit("她感到无比震惊。这一切终于结束了。")

        self.assertIn("ai_flavor", report)
        self.assertGreaterEqual(report["ai_flavor"]["emotion_telling_hits"], 1)
        self.assertTrue(any(issue["type"] == "ai_flavor" for issue in report["issues"]))

    def test_context_builder_includes_debt_constraints(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_secret({
            "id": "SEC_001",
            "title": "父亲的真实身份",
            "status": "hidden",
            "description": "父亲其实是组织的卧底",
            "chapter_id": "001",
        })
        store.upsert_reader_promise({
            "id": "RP_001",
            "title": "主角会找到父亲",
            "status": "open",
            "description": "读者期待主角找到父亲的真相",
            "chapter_id": "001",
        })
        agent = ContextBuilderAgent(self.tmpdir)
        context = agent.build(
            "测试目标",
            {"scene_id": "002-01", "target_chars": [100, 200], "purpose": "测试"},
        )
        self.assertIn("剧情债务约束", context)
        self.assertIn("父亲的真实身份", context)
        self.assertIn("主角会找到父亲", context)

    def test_vector_index_failure_writes_report_without_failing(self):
        class FailingVectorStore:
            def upsert(self, chunks):
                raise RuntimeError("embedding down")

        config = PipelineConfig(root_dir=self.tmpdir, llm=StaticLLM({}))
        orchestrator = NovelOrchestrator(config)
        orchestrator.vector_store = FailingVectorStore()
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001" / "reports"
        chapter_dir.mkdir(parents=True)

        orchestrator.chapter_post._index_to_vector_store("001", {}, "第一段正文", "章节总结", {})
        report = json.loads((chapter_dir / "vector_index.json").read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "failed")
        self.assertIn("embedding down", report["error"])

    def test_chief_editor_outline_contains_genre_genes(self):
        from novel_agent.agents.chief_editor import ChiefEditorAgent
        llm = StaticLLM({"chief_editor": json.dumps({
            "title_options": ["《枪声破晓》"],
            "protagonist": {"name": "沈星璃"},
            "macro_outline": [{"arc_id": "A01", "chapters": "1-20", "goal": "打进职业圈"}],
        }, ensure_ascii=False)})

        outline = ChiefEditorAgent(llm).plan_novel("电竞逆袭", "电竞", 20)

        self.assertIn("genre_genes", outline)
        self.assertIn("pleasure_mechanism", outline["genre_genes"])

    def test_orchestrator_writes_scale_profile_to_outline(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        orchestrator = NovelOrchestrator(config)

        orchestrator.run_novel(theme="短篇测试", genre="悬疑", target_chapters=2)

        outline = json.loads((self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8"))
        self.assertEqual(outline["scale_profile"]["scale"], "micro")

    def test_orchestrator_uses_profile_calibration_interval(self):
        from novel_agent.control.scale_profile import resolve_scale_profile
        profile = resolve_scale_profile(target_chapters=80)
        self.assertEqual(profile["calibration_interval"], 20)

    def test_orchestrator_generates_quality_report(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        orchestrator = NovelOrchestrator(config)
        results = orchestrator.run_novel(
            theme="测试主题",
            genre="玄幻",
            target_chapters=1,
        )
        self.assertTrue(len(results) >= 1)
        chapter_id = results[0].chapter_id
        quality_path = self.tmpdir / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports" / "quality.json"
        self.assertTrue(quality_path.exists())
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        self.assertEqual(quality["mode"], "report_only")
        self.assertIn("style", quality["checks"])


if __name__ == "__main__":
    unittest.main()
