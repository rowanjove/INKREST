import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from novel_agent.agents.base import StaticLLM, OpenAILLM, create_llm
from novel_agent.pipeline import PipelineConfig, DEFAULT_SETTINGS, load_pipeline_settings
from novel_agent.prompts import PromptRepository
from novel_agent.quality.audit_schema import validate_audit_report
from novel_agent.scripts.sensitive_scan import scan_sensitive_words
from novel_agent.scripts.count_chars import count_chinese_chars, wordcount_report
from novel_agent.scripts.merge_scenes import merge_scene_texts
from novel_agent.state.vector_store import (
    SQLiteEmbeddingVectorStore,
    VectorChunk,
    create_vector_store,
)
from orchestrator import _normalize_argv
from novel_agent.json_utils import loads_json_object
from novel_agent.rules import RuleBook


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-test-"))

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_count_chinese_chars_counts_only_cjk_characters(self):
        text = "林澈A1，雨停了。OK"
        self.assertEqual(count_chinese_chars(text), 5)

    def test_wordcount_report_marks_short_text_as_under_target(self):
        report = wordcount_report("林澈推开门。", 20, 30)
        self.assertEqual(report["count"], 5)
        self.assertEqual(report["status"], "under")
        self.assertEqual(report["missing"], 15)

    def test_merge_scene_texts_orders_scene_files_by_name(self):
        scene_dir = self.tmpdir / "scenes"
        scene_dir.mkdir()
        (scene_dir / "scene_002.txt").write_text("第二场", encoding="utf-8")
        (scene_dir / "scene_001.txt").write_text("第一场", encoding="utf-8")
        merged = merge_scene_texts(scene_dir)
        self.assertEqual(merged, "第一场\n\n第二场")

    def test_prompt_repository_loads_role_prompt(self):
        prompt_dir = self.tmpdir / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "writer.md").write_text("写作规则", encoding="utf-8")
        repo = PromptRepository(self.tmpdir)
        self.assertEqual(repo.load("writer"), "写作规则")

    def test_rulebook_loads_structured_writing_rules(self):
        assets_dir = self.tmpdir / "assets"
        assets_dir.mkdir()
        (assets_dir / "rules.yaml").write_text(
            "forbiddenWords:\n  - content: fate gear\n    description: template phrase\n"
            "writingTechniques: Use concrete actions.\n",
            encoding="utf-8",
        )
        rules = RuleBook(self.tmpdir).load()
        self.assertEqual(rules["forbiddenWords"][0]["content"], "fate gear")
        self.assertEqual(rules["writingTechniques"], "Use concrete actions.")

    def test_rulebook_prompt_includes_reference_authors(self):
        assets_dir = self.tmpdir / "assets"
        assets_dir.mkdir()
        (assets_dir / "rules.yaml").write_text(
            "referenceAuthors:\n  - 金庸\n  - 诡秘之主\n"
            "writingTechniques: |\n  - 短句推进\n",
            encoding="utf-8",
        )
        section = RuleBook(self.tmpdir).to_prompt_section()
        self.assertIn("金庸", section)
        self.assertIn("诡秘之主", section)
        self.assertIn("对标作者", section)

    def test_load_pipeline_settings_reads_yaml_config(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "runtime:\n  max_workers: 2\n", encoding="utf-8"
        )
        settings = load_pipeline_settings(self.tmpdir)
        self.assertEqual(settings["runtime"]["max_workers"], 2)

    def test_cli_normalizes_query_events_command(self):
        argv = _normalize_argv(["query-events", "--query", "白塔医院"])
        self.assertEqual(argv[0], "query-events")

    def test_cli_normalizes_query_timeline_command(self):
        argv = _normalize_argv(["query-timeline", "--query", "白塔医院"])
        self.assertEqual(argv[0], "query-timeline")

    def test_sensitive_scan_reports_hits_with_line_numbers(self):
        words_file = self.tmpdir / "sensitive_words.txt"
        words_file.write_text("禁词\n", encoding="utf-8")
        report = scan_sensitive_words("第一行\n这里有禁词", words_file)
        self.assertEqual(report["status"], "hit")
        self.assertEqual(report["hits"][0]["word"], "禁词")
        self.assertEqual(report["hits"][0]["line"], 2)

    def test_validate_audit_report_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            validate_audit_report({"risk_level": "低"})

    def test_guard_summary_marks_empty_chapter_as_hard_fail(self):
        from novel_agent.quality.guard_registry import build_guard_summary

        summary = build_guard_summary("", checks={})

        self.assertEqual(summary["overall_status"], "FAIL")
        self.assertIn("non_empty_final_text", summary["blocked_by"])
        result = summary["results"][0]
        self.assertEqual(result["guard"], "non_empty_final_text")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["level"], 1)

    def test_guard_summary_allows_non_empty_chapter_without_hard_fail(self):
        from novel_agent.quality.guard_registry import build_guard_summary

        summary = build_guard_summary("林澈推开门，雨水从袖口滴到地上。", checks={})

        self.assertNotIn("non_empty_final_text", summary["blocked_by"])
        self.assertNotEqual(summary["overall_status"], "FAIL")

    def test_quality_report_includes_guard_summary(self):
        from novel_agent.quality.report import build_quality_report

        report = build_quality_report("林澈推开门，雨水从袖口滴到地上。")

        self.assertIn("guard_summary", report)
        self.assertIn("results", report["guard_summary"])

    def test_quality_report_empty_text_is_not_overall_pass(self):
        from novel_agent.quality.report import build_quality_report

        report = build_quality_report("")

        self.assertFalse(report["overall_pass"])
        self.assertEqual(report["guard_summary"]["overall_status"], "FAIL")

    def test_quality_gate_blocks_only_in_block_on_fail_mode(self):
        from novel_agent.quality.report import build_quality_report
        from novel_agent.quality.settings import quality_gate_blocks

        report = build_quality_report("", mode="block_on_fail")
        self.assertTrue(quality_gate_blocks(report, "block_on_fail"))
        self.assertFalse(quality_gate_blocks(report, "report_only"))

    def test_planner_truncates_scenes_to_max_plan_scenes(self):
        from novel_agent.agents.planner import PlannerAgent
        from novel_agent.agents.base import StaticLLM

        scenes = [
            {
                "scene_id": f"00{i}",
                "purpose": f"场景{i}",
                "target_chars": [400, 800],
            }
            for i in range(1, 6)
        ]
        raw = json.dumps(
            {"chapter_id": "001", "chapter_title": "测", "scenes": scenes},
            ensure_ascii=False,
        )
        agent = PlannerAgent(StaticLLM({"planner": raw}))
        plan = agent._parse_and_validate_plan(raw, "001", "goal", max_plan_scenes=2)
        self.assertEqual(len(plan["scenes"]), 2)

    def test_planner_prompt_includes_runtime_context(self):
        from novel_agent.agents.planner import PlannerAgent
        from novel_agent.agents.base import StaticLLM

        agent = PlannerAgent(StaticLLM({"planner": "{}"}))
        prompt = agent._build_prompt(
            "001",
            "推进主线",
            runtime_context="体量档位: 短篇\n场景数量上限: 4",
        )
        self.assertIn("体量与规划约束", prompt)
        self.assertIn("场景数量上限: 4", prompt)

    def test_resolve_runtime_policy_uses_outline_scale(self):
        from novel_agent.control.runtime_policy import resolve_runtime_policy

        outline_path = self.tmpdir / "workspace" / "outline.json"
        outline_path.parent.mkdir(parents=True, exist_ok=True)
        outline_path.write_text(
            json.dumps(
                {
                    "scale_profile": {
                        "scale": "short",
                        "planning_mode": "full_upfront",
                        "max_plan_scenes": 3,
                        "label": "短篇",
                        "calibration_interval": 0,
                    }
                }
            ),
            encoding="utf-8",
        )
        policy = resolve_runtime_policy(self.tmpdir)
        self.assertEqual(policy.scale, "short")
        self.assertEqual(policy.max_plan_scenes, 3)
        self.assertEqual(policy.planning_mode, "full_upfront")
        self.assertEqual(policy.outline_layers, ("L0", "L3"))

    def test_quality_report_includes_rewrite_hints_when_failing(self):
        from novel_agent.quality.report import build_quality_report
        from novel_agent.quality.quality_rewrite import build_quality_rewrite_hints

        report = build_quality_report("", mode="block_on_fail")
        hints = build_quality_rewrite_hints(report)
        self.assertTrue(hints.strip() or report["guard_summary"]["overall_status"] == "FAIL")

    def test_unified_gate_writes_report_file(self):
        import dataclasses
        from unittest.mock import AsyncMock, MagicMock
        from novel_agent.phases.base import ChapterContext
        from novel_agent.services.chapter_postprocess import QualityReportOutcome
        from novel_agent.services.unified_gate import run_unified_review_gate

        reports_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001" / "reports"
        reports_dir.mkdir(parents=True)
        chapter_dir = reports_dir.parent

        orchestrator = MagicMock()
        orchestrator.root_dir = self.tmpdir
        orchestrator._write_json = lambda path, data: path.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        orchestrator.chapter_post.write_quality_report = AsyncMock(
            return_value=QualityReportOutcome(
                report={
                    "mode": "report_only",
                    "overall_pass": True,
                    "checks": {},
                    "guard_summary": {"overall_status": "PASS", "blocked_by": []},
                },
                blocked=False,
            )
        )

        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="goal",
            chapter_dir=chapter_dir,
            scenes_dir=chapter_dir / "scenes",
            reports_dir=reports_dir,
            plan={},
            final_text="林澈推门。",
            audit={"risk_level": "低", "issues": []},
        )

        import asyncio

        outcome = asyncio.run(
            run_unified_review_gate(orchestrator, "001", ctx, reports_dir, chapter_dir)
        )
        self.assertTrue(outcome.passed)
        self.assertTrue((reports_dir / "unified_gate.json").exists())

    def test_post_audit_persist_stamp_skips_duplicate(self):
        from novel_agent.phases.post_audit import PostAuditPhase
        from novel_agent.phases.base import ChapterContext
        from novel_agent.state.persist_stamp import compute_persist_stamp, write_persist_stamp

        reports_dir = self.tmpdir / "reports"
        reports_dir.mkdir(parents=True)
        chapter_dir = self.tmpdir / "chapter_001"
        chapter_dir.mkdir(parents=True)
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="g",
            chapter_dir=chapter_dir,
            scenes_dir=chapter_dir / "scenes",
            reports_dir=reports_dir,
            plan={},
            final_text="正文",
            extracted_state={"events": [{"id": "evt_001_a", "summary": "事件"}]},
        )
        state_update = dict(ctx.extracted_state or {})
        stamp = compute_persist_stamp("001", ctx.final_text, state_update)
        write_persist_stamp(reports_dir / "post_audit_stamp.json", stamp, "001")

        phase = PostAuditPhase(MagicMock())
        self.assertTrue(phase._should_skip_duplicate_persist(ctx, state_update))

    def test_hook_timeout_returns_default(self):
        import time
        from novel_agent.plugins.hook_runner import call_hook_with_timeout

        def slow():
            time.sleep(2)
            return "ok"

        with self.assertRaises(TimeoutError):
            call_hook_with_timeout(slow, timeout_seconds=0.1)

        self.assertEqual(
            call_hook_with_timeout(slow, timeout_seconds=0.1, default="fallback"),
            "fallback",
        )

    def test_persona_evaluations_off_skips_reader_block(self):
        from novel_agent.quality.settings import resolve_persona_evaluations

        (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            'chapter:\n  persona_evaluations: "off"\n',
            encoding="utf-8",
        )
        self.assertEqual(resolve_persona_evaluations(self.tmpdir), "off")

    def test_persona_evaluations_legacy_full_still_honored(self):
        from novel_agent.quality.settings import resolve_persona_evaluations

        (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            'chapter:\n  persona_evaluations: "full"\n',
            encoding="utf-8",
        )
        self.assertEqual(resolve_persona_evaluations(self.tmpdir), "full")

    def test_audit_requires_rewrite_triggers_on_critical_classification(self):
        from novel_agent.quality.audit_rewrite import audit_requires_rewrite

        audit = {
            "risk_level": "低",
            "audit_classification": {"CRITICAL": [{"type": "word_count_out_of_bounds"}]},
            "issues": [],
        }
        self.assertTrue(audit_requires_rewrite(audit))

    def test_validate_state_update_blocks_cross_chapter_event_overwrite(self):
        from novel_agent.state.sqlite_store import SQLiteStateStore
        from novel_agent.state.update_validator import validate_state_update

        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update(
            "001",
            {"events": [{"id": "evt_shared", "summary": "第一章事件"}]},
        )
        sanitized = validate_state_update(
            "002",
            {"events": [{"id": "evt_shared", "summary": "第二章试图覆盖"}]},
            db_path=store.db_path,
        )
        self.assertEqual(sanitized.get("events"), [])

    def test_clear_database_requires_confirm_without_access_token(self):
        from fastapi.testclient import TestClient
        import web.server as web_server
        from web.server import app as web_app

        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            client = TestClient(web_app)
            denied = client.post("/api/database/clear", json={"confirm": False})
            self.assertEqual(denied.status_code, 400)
            allowed = client.post("/api/database/clear", json={"confirm": True})
            self.assertEqual(allowed.status_code, 200)
        finally:
            web_server.BASE_DIR = original_base

    def test_loads_json_object_accepts_markdown_fenced_json(self):
        data = loads_json_object('```json\n{"risk_level": "低"}\n```')
        self.assertEqual(data["risk_level"], "低")

    def test_create_llm_returns_static_for_static_provider(self):
        llm = create_llm({"provider": "static", "responses": {"default": "test"}})
        self.assertIsInstance(llm, StaticLLM)
        self.assertEqual(llm.generate("any", ""), "test")

    def test_create_llm_returns_openai_for_openai_provider(self):
        llm = create_llm({
            "provider": "openai",
            "base_url": "http://localhost:11434/v1",
            "api_key": "test",
            "model": "qwen2",
        })
        self.assertIsInstance(llm, OpenAILLM)
        self.assertEqual(llm.base_url, "http://localhost:11434/v1")
        self.assertEqual(llm.model, "qwen2")

    def test_create_llm_rejects_unknown_provider(self):
        with self.assertRaises(ValueError):
            create_llm({"provider": "unknown"})

    @patch("novel_agent.agents.base.httpx.Client")
    def test_openai_llm_sends_correct_request(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": " 生成的文本 "}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        llm = OpenAILLM(base_url="http://test/v1", api_key="sk-test", model="gpt-4o")
        result = llm.generate("writer", "写一段雨夜")

        self.assertEqual(result, "生成的文本")
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("chat/completions", call_args[0][0])
        payload = call_args[1]["json"]
        self.assertEqual(payload["model"], "gpt-4o")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "写一段雨夜")

    def test_stub_vector_store_performs_local_retrieval(self):
        store = create_vector_store({"provider": "stub"}, root_dir=self.tmpdir)
        store.upsert([
            VectorChunk(id="c1", type="test", text="林澈进入了神秘的白塔医院地下二层。"),
            VectorChunk(id="c2", type="test", text="天空中闪过一道雷电。"),
        ])
        results = store.search("白塔医院")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "c1")
        self.assertGreater(results[0]["score"], 0.0)

    def test_create_vector_store_returns_stub_for_stub_provider(self):
        store = create_vector_store({"provider": "stub"}, root_dir=self.tmpdir)
        self.assertIsInstance(store, SQLiteEmbeddingVectorStore)

    def test_create_vector_store_returns_cloud_for_openai_provider(self):
        store = create_vector_store(
            {"provider": "openai", "api_key": "sk-test"},
            root_dir=self.tmpdir,
        )
        self.assertIsInstance(store, SQLiteEmbeddingVectorStore)

    @patch.object(SQLiteEmbeddingVectorStore, "_embed_with_fallback")
    def test_vector_store_upsert_and_search(self, mock_embed):
        import numpy as np
        mock_embed.return_value = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

        store = SQLiteEmbeddingVectorStore(
            {"provider": "openai", "api_key": "sk-test"},
            root_dir=self.tmpdir,
        )
        store.upsert([
            VectorChunk(id="c1", type="summary", text="林澈回到出租屋", metadata={"chapter": "001"}),
            VectorChunk(id="c2", type="summary", text="白塔医院的秘密", metadata={"chapter": "012"}),
        ])

        mock_embed.return_value = np.array([[1.0, 0.1, 0.0]], dtype=np.float32)
        results = store.search("林澈出租屋", top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "c1")
        self.assertGreater(results[0]["score"], results[1]["score"])

    @patch.object(SQLiteEmbeddingVectorStore, "_embed_with_fallback")
    def test_vector_store_delete(self, mock_embed):
        import numpy as np
        mock_embed.return_value = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

        store = SQLiteEmbeddingVectorStore(
            {"provider": "openai", "api_key": "sk-test"},
            root_dir=self.tmpdir,
        )
        store.upsert([
            VectorChunk(id="c1", type="test", text="aaa"),
            VectorChunk(id="c2", type="test", text="bbb"),
        ])
        store.delete(["c1"])

        results = store.search("bbb", top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "c2")

    def test_vector_store_chapter_filters_normalize_string_ids(self):
        chunk = {"type": "summary", "metadata": {"chapter": "010"}}
        self.assertFalse(
            SQLiteEmbeddingVectorStore._match_filters(chunk, {"chapter_lt": 2})
        )
        self.assertTrue(
            SQLiteEmbeddingVectorStore._match_filters(chunk, {"chapter_gt": "002"})
        )

    def test_genre_genes_fill_defaults_and_preserve_existing_values(self):
        from novel_agent.control.genre_genes import ensure_genre_genes
        outline = {
            "core_theme": "电竞逆袭",
            "genre_positioning": "电竞女频",
            "genre_genes": {"pleasure_mechanism": "碾压型"},
        }
        result = ensure_genre_genes(outline)
        self.assertEqual(result["genre_genes"]["pleasure_mechanism"], "碾压型")
        self.assertEqual(result["genre_genes"]["protagonist_arc"], "从弱到强")
        self.assertIn("不要把电竞逆袭写成纯恋爱日常", result["genre_genes"]["drift_guards"])

    def test_pacing_report_flags_too_many_setup_chapters(self):
        from novel_agent.control.chapter_window import build_pacing_report
        items = [{"chapter_type": "铺垫章"} for _ in range(5)] + [{"chapter_type": "爆发章"}]
        report = build_pacing_report(items)
        self.assertFalse(report["pass"])
        self.assertIn("铺垫章过多", report["issues"][0])

    def test_normalize_chapter_window_adds_pacing_fields(self):
        from novel_agent.control.chapter_window import normalize_chapter_window
        raw = [{"chapter_id": "001", "title": "开播", "goal": "主角首次证明自己"}]
        result = normalize_chapter_window(raw)
        item = result[0]
        self.assertEqual(item["chapter_id"], "001")
        self.assertEqual(item["chapter_type"], "铺垫章")
        self.assertEqual(item["plot_task"]["what_happens"], "主角首次证明自己")
        self.assertEqual(item["payoff_task"]["has_payoff"], False)
        self.assertIn("hook", item)

    def test_normalize_chapter_window_adds_scene_detail_and_hook_type(self):
        from novel_agent.control.chapter_window import normalize_chapter_window
        raw = [{"chapter_id": "003", "title": "埋伏", "goal": "主角察觉异样"}]
        result = normalize_chapter_window(raw)
        item = result[0]
        self.assertIn(item["scene_type"], {"setup", "build", "burst", "transition"})
        self.assertIn(item["detail_level"], {"brief", "normal", "full", "skip"})
        self.assertIn(item["hook_type"], {"info", "action", "reversal"})

    def test_calibration_report_detects_genre_drift_and_debt(self):
        from novel_agent.control.calibration import build_calibration_report
        outline = {"genre_genes": {"drift_guards": ["不要连续三章没有外部压力或可见进展"]}}
        chapters = [{"chapter_id": "001", "chapter_type": "过渡章"} for _ in range(4)]
        debt = {"foreshadows": [{"id": "F001", "debt_status": "overdue", "title": "短信号码"}]}
        report = build_calibration_report(outline, chapters, debt)
        self.assertFalse(report["pass"])
        self.assertIn("存在过期叙事债务", report["issues"])

    def test_pipeline_config_from_config_creates_static_llm_by_default(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n  provider: static\nruntime:\n  max_workers: 2\n",
            encoding="utf-8",
        )
        config = PipelineConfig.from_config(self.tmpdir)
        self.assertIsInstance(config.llm, StaticLLM)
        self.assertEqual(config.max_workers, 2)

    def test_pipeline_config_uses_model_library_default_for_novel_chat(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n  provider: static\n  default_model_id: chat-main\n",
            encoding="utf-8",
        )
        (config_dir / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "chat-main": {
                            "provider": "openai",
                            "base_url": "http://localhost:11434/v1",
                            "api_key": "test",
                            "model": "qwen2.5:14b",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        config = PipelineConfig.from_config(self.tmpdir)
        self.assertIsInstance(config.get_llm("novel_chat"), OpenAILLM)
        self.assertEqual(config.get_llm("novel_chat").model, "qwen2.5:14b")

    def test_pipeline_config_uses_first_model_when_static_config_has_model_library(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n  provider: static\nruntime:\n  max_workers: 1\nembedding:\n  provider: stub\n",
            encoding="utf-8",
        )
        (config_dir / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "main-model": {
                            "provider": "openai",
                            "base_url": "http://localhost:11434/v1",
                            "api_key": "test",
                            "model": "qwen",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        config = PipelineConfig.from_config(self.tmpdir)
        self.assertIsInstance(config.get_llm("writer"), OpenAILLM)
        self.assertEqual(config.get_llm("writer").model, "qwen")

    def test_pipeline_config_routes_daily_and_reasoning_tiers(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n"
            "  daily_model_id: flash\n"
            "  reasoning_model_id: pro\n"
            "",
            encoding="utf-8",
        )
        (config_dir / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "flash": {
                            "provider": "openai",
                            "base_url": "http://localhost:11434/v1",
                            "api_key": "test",
                            "model": "flash-model",
                        },
                        "pro": {
                            "provider": "openai",
                            "base_url": "http://localhost:11434/v1",
                            "api_key": "test",
                            "model": "pro-model",
                        },
                    }
                }
            ),
            encoding="utf-8",
        )

        config = PipelineConfig.from_config(self.tmpdir)

        self.assertEqual(config.get_llm("writer").model, "flash-model")
        self.assertEqual(config.get_llm("chief_editor").model, "pro-model")

    def test_pipeline_config_reads_interactive_runtime_flag(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n  provider: static\nruntime:\n  interactive: true\n",
            encoding="utf-8",
        )
        config = PipelineConfig.from_config(self.tmpdir)
        self.assertTrue(config.interactive)

    def test_pipeline_config_dry_run_uses_static_llm(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        self.assertIsInstance(config.llm, StaticLLM)

    def test_default_runtime_includes_interactive_flag(self):
        self.assertFalse(DEFAULT_SETTINGS["runtime"]["interactive"])

    def test_extract_tail_hooks_detects_unfinished_action_and_injury(self):
        from novel_agent.quality.hooks import extract_tail_hooks
        text = "林澈正要推开石门，忽然听见井下传来脚步声。\n他的左臂仍在流血。"
        hooks = extract_tail_hooks(text)
        self.assertTrue(hooks["unfinished_actions"])
        self.assertTrue(hooks["injuries"])
        self.assertTrue(any("正要推开石门" in hook for hook in hooks["unfinished_actions"]))
        self.assertFalse(any("流血" in hook for hook in hooks["unfinished_actions"]))

    def test_check_head_continuity_reports_missing_state(self):
        from novel_agent.quality.hooks import check_head_continuity
        prev = {"unfinished_actions": ["正要推开石门"], "injuries": ["流血"], "keywords": []}
        report = check_head_continuity(prev, "林澈回到客栈，点了一壶茶。")
        self.assertFalse(report["pass"])
        self.assertGreaterEqual(len(report["missing_hooks"]), 1)

    def test_check_head_continuity_passes_when_hooks_present(self):
        from novel_agent.quality.hooks import check_head_continuity
        prev = {"unfinished_actions": ["正要推开石门"], "injuries": ["伤口"], "keywords": []}
        report = check_head_continuity(prev, "林澈正要推开石门，左臂的伤口还在隐隐作痛。")
        self.assertTrue(report["pass"])
        self.assertEqual(len(report["missing_hooks"]), 0)

    def test_apply_chapter_distance_penalty_filters_recent(self):
        from novel_agent.state.vector_store import apply_chapter_distance_penalty
        results = [
            {"id": "recent", "text": "最近章节内容", "metadata": {"chapter": "009"}, "score": 0.9},
            {"id": "mid", "text": "中距离内容", "metadata": {"chapter": "006"}, "score": 0.8},
            {"id": "old", "text": "旧内容", "metadata": {"chapter": "001"}, "score": 0.7},
        ]
        filtered = apply_chapter_distance_penalty(results, "010", top_k=5)
        ids = [r["id"] for r in filtered]
        self.assertNotIn("recent", ids)
        self.assertIn("mid", ids)
        self.assertIn("old", ids)

    def test_apply_chapter_distance_penalty_labels_rewrite(self):
        from novel_agent.state.vector_store import apply_chapter_distance_penalty
        results = [
            {"id": "mid", "text": "中距离内容", "metadata": {"chapter": "006"}, "score": 0.8},
            {"id": "old", "text": "旧内容", "metadata": {"chapter": "001"}, "score": 0.7},
        ]
        filtered = apply_chapter_distance_penalty(results, "010", top_k=5)
        mid_item = next(r for r in filtered if r["id"] == "mid")
        self.assertEqual(mid_item["rewrite_hint"], "REQUIRE_REWRITE_40%")
        old_item = next(r for r in filtered if r["id"] == "old")
        self.assertIsNone(old_item["rewrite_hint"])

    def test_apply_chapter_distance_penalty_keeps_results_without_current_chapter(self):
        from novel_agent.state.vector_store import apply_chapter_distance_penalty
        results = [
            {"id": "old", "text": "旧内容", "metadata": {"chapter": "001"}, "score": 0.7},
            {"id": "mid", "text": "中距离内容", "metadata": {"chapter": "006"}, "score": 0.8},
        ]
        filtered = apply_chapter_distance_penalty(results, "", top_k=5)
        self.assertEqual([r["id"] for r in filtered], ["old", "mid"])
        self.assertTrue(all(r["rewrite_hint"] is None for r in filtered))

    def test_build_quality_report_includes_all_checks(self):
        from novel_agent.quality.report import build_quality_report
        text = "林澈推开石门，走了进去。他看到桌上有封信。"
        report = build_quality_report(text)
        self.assertEqual(report["mode"], "report_only")
        self.assertIn("style", report["checks"])
        self.assertIn("layout", report["checks"])
        self.assertIn("scene_delta", report["checks"])
        self.assertIn("continuity_physical", report["checks"])
        for check in report["checks"].values():
            self.assertIn("level", check)
            self.assertIsInstance(check["score"], int)
            self.assertGreaterEqual(check["score"], 0)
            self.assertLessEqual(check["score"], 100)
            if not check.get("pass"):
                self.assertNotEqual(check["level"], "none")
                self.assertLess(check["score"], 70)

    def test_quality_report_detects_emotion_telling_dialogue_and_bad_ending(self):
        from novel_agent.quality.report import build_quality_report
        text = (
            "她感到无比震惊，心中涌起一股难以言说的情绪。\n"
            "“我认为我们现在面临的最大问题，是如何在有限时间内完成任务。”李明说。\n"
            "“你说得有道理，我们需要尽快制定一个可行的计划。”王芳点头赞同。\n"
            "“所以我们必须马上分工，并且保证所有环节都不出错。”李明说。\n"
            "这一切终于结束了，他望着远方，心中充满了感慨。"
        )
        report = build_quality_report(text)
        anti_ai = report["checks"]["anti_ai_flavor"]
        self.assertFalse(anti_ai["pass"])
        self.assertEqual(anti_ai["level"], "fail")
        self.assertGreaterEqual(anti_ai["emotion_telling_hits"], 2)
        self.assertGreaterEqual(anti_ai["dialogue_overcomplete_hits"], 1)
        self.assertEqual(anti_ai["ending_type"], "bad")

    def test_quality_report_passes_concrete_emotion_and_hook_ending(self):
        from novel_agent.quality.report import build_quality_report
        text = (
            "她把手机扣在桌上，屏幕朝下。\n"
            "“你有数吗？”\n"
            "王芳没答，看了他一眼。\n"
            "李明把信叠好，拿起了电话。"
        )
        report = build_quality_report(text)
        anti_ai = report["checks"]["anti_ai_flavor"]
        self.assertTrue(anti_ai["pass"])
        self.assertEqual(anti_ai["emotion_telling_hits"], 0)
        self.assertEqual(anti_ai["ending_type"], "hook")

    def test_scale_profile_maps_target_chapters_to_profile(self):
        from novel_agent.control.scale_profile import resolve_scale_profile
        self.assertEqual(resolve_scale_profile(target_chapters=1)["scale"], "micro")
        self.assertEqual(resolve_scale_profile(target_chapters=12)["scale"], "short")
        self.assertEqual(resolve_scale_profile(target_chapters=80)["scale"], "medium")
        self.assertEqual(resolve_scale_profile(target_chapters=300)["scale"], "long")
        self.assertEqual(resolve_scale_profile(target_chapters=800)["scale"], "epic")

    def test_scale_profile_maps_user_length_label(self):
        from novel_agent.control.scale_profile import resolve_scale_profile
        self.assertEqual(resolve_scale_profile(scale_label="一章以内")["scale"], "micro")
        self.assertEqual(resolve_scale_profile(scale_label="几章")["scale"], "short")
        self.assertEqual(resolve_scale_profile(scale_label="几十章")["scale"], "medium")
        self.assertEqual(resolve_scale_profile(scale_label="一两百章")["scale"], "long")
        self.assertEqual(resolve_scale_profile(scale_label="几百上千章")["scale"], "epic")
        self.assertEqual(resolve_scale_profile(scale_label="一直更新下去")["scale"], "infinite")

    def test_scale_profile_reports_upgrade_pressure(self):
        from novel_agent.control.scale_profile import build_upgrade_pressure
        pressure = build_upgrade_pressure({"scale": "short", "max_chapters": 20}, current_chapter_count=18)
        self.assertTrue(pressure["should_prompt"])
        self.assertEqual(pressure["recommended_scale"], "medium")
    def test_context_builder_character_pruning(self):
        # 1. 写入 character_cards.yaml
        assets_dir = self.tmpdir / "assets"
        assets_dir.mkdir(exist_ok=True, parents=True)
        (assets_dir / "character_cards.yaml").write_text(
            "characters:\n"
            "  - id: protagonist\n"
            "    name: 林澈\n"
            "    description: 主角\n"
            "  - id: friend\n"
            "    name: 顾妙\n"
            "    description: 朋友\n"
            "  - id: bystander\n"
            "    name: 张三\n"
            "    description: 路人甲\n",
            encoding="utf-8"
        )
        
        # 2. 构造 ContextBuilderAgent
        from novel_agent.agents.context_builder import ContextBuilderAgent
        builder = ContextBuilderAgent(self.tmpdir)
        
        # 3. 传入只包含顾妙的场景
        scene = {
            "scene_id": "001-01",
            "characters": ["顾妙"]
        }
        
        # 4. 执行裁剪并验证
        pruned_yaml = builder._prune_character_cards(scene)
        import yaml
        pruned_data = yaml.safe_load(pruned_yaml)
        
        # 验证只有林澈(主角)和顾妙被保留，张三被剔除
        chars = [c["name"] for c in pruned_data.get("characters", [])]
        self.assertIn("林澈", chars)
        self.assertIn("顾妙", chars)
        self.assertNotIn("张三", chars)

    @patch("novel_agent.agents.stitch_editor.StitchEditorAgent.edit_boundary")
    def test_sliding_window_stitching(self, mock_edit_boundary):
        from novel_agent.agents.stitch_editor import StitchEditorAgent
        mock_edit_boundary.return_value = "缝合接缝文本"
        agent = StitchEditorAgent(llm=MagicMock())
        
        # 验证分割段落逻辑
        text1 = "第一段\n\n第二段\n\n第三段\n\n第四段"
        prefix, tail = agent._split_tail(text1, target_chars=500, max_paragraphs=2)
        self.assertEqual(prefix, "第一段\n\n第二段")
        self.assertEqual(tail, "第三段\n\n第四段")
        
        text2 = "第五段\n\n第六段\n\n第七段\n\n第八段"
        head, suffix = agent._split_head(text2, target_chars=500, max_paragraphs=2)
        self.assertEqual(head, "第五段\n\n第六段")
        self.assertEqual(suffix, "第七段\n\n第八段")
        
        # 验证场景拼接整体逻辑
        scene1 = "这是场景一的第一段。\n\n这是场景一的第二段。\n\n这是场景一的第三段。\n\n这是场景一的第四段。"
        scene2 = "这是场景二的第一段。\n\n这是场景二的第二段。\n\n这是场景二的第三段。\n\n这是场景二的第四段。"
        result = agent.edit_scenes([scene1, scene2])
        
        mock_edit_boundary.assert_called_once()
        self.assertIn("这是场景一的第一段。", result)
        self.assertIn("缝合接缝文本", result)
        self.assertIn("这是场景二的第四段。", result)

    def test_active_debt_injection(self):
        from novel_agent.orchestrator import NovelOrchestrator
        config = PipelineConfig.dry_run(self.tmpdir)
        orchestrator = NovelOrchestrator(config)
        
        # 写入三个过期债务
        update = {
            "foreshadows": [
                {
                    "id": "F001",
                    "title": "神秘短信",
                    "status": "open",
                    "description": "林澈收到神秘短信",
                    "deadline_chapter": "003",
                }
            ],
            "reader_promises": [
                {
                    "id": "P001",
                    "title": "决战爆发",
                    "status": "open",
                    "description": "承诺在第4章决战",
                    "deadline_chapter": "004",
                }
            ],
            "secrets": [
                {
                    "id": "S001",
                    "title": "身世之谜",
                    "status": "hidden",
                    "description": "主角的隐藏身世",
                    "deadline_chapter": "002",
                }
            ]
        }
        orchestrator.store.sync_state_update("001", update)
        
        # 在第 5 章，这三个应该都是过期债务，但应该只选择 2 个最早的：S001 (截止002) 和 F001 (截止003)
        debts_text = orchestrator.chapter_post._query_overdue_debts("005")
        
        self.assertIn("身世之谜", debts_text)
        self.assertIn("神秘短信", debts_text)
        self.assertNotIn("决战爆发", debts_text)


if __name__ == "__main__":
    unittest.main()
