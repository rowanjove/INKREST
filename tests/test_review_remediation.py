from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from novel_agent.agents.base import StaticLLM
from novel_agent.agents.chief_editor import ChiefEditorAgent
from novel_agent.agents.length_fix import LengthFixAgent
from novel_agent.agents.planner import PlannerAgent
from novel_agent.exceptions import LLMResponseError
from novel_agent.domain.tasks import TaskStatus, TaskType
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.phases.base import ChapterContext
from novel_agent.phases.generation import (
    GenerationPhase,
    _raise_if_too_many_scene_failures,
    sanitize_scene_id,
)
from novel_agent.pipeline import PipelineConfig
from novel_agent.plugins.manager import PluginManager
from novel_agent.quality.audit_schema import build_audit_error
from novel_agent.services.hierarchical_summary import assemble_hierarchical_context
from novel_agent.services.manuscript_workspace import read_chapter_plain_text
from novel_agent.state.schema_version import SchemaState
from novel_agent.state.sqlite_store import SQLiteStateStore


class ReviewRemediationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="review-fix-"))

    def test_sanitize_scene_id_blocks_path_escape(self):
        self.assertEqual(sanitize_scene_id("001-01", fallback="scene"), "001-01")
        self.assertNotIn("..", sanitize_scene_id("../../evil", fallback="scene"))
        self.assertNotIn("/", sanitize_scene_id("a/b/c", fallback="scene"))
        first = sanitize_scene_id("开场", fallback="scene")
        second = sanitize_scene_id("高潮", fallback="scene")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("scene_"))

    def test_partial_scene_failures_abort_generation(self):
        with self.assertRaises(RuntimeError):
            _raise_if_too_many_scene_failures([{"scene_id": "1"}, {"scene_id": "2"}], 3)
        _raise_if_too_many_scene_failures([{"scene_id": "1"}], 4)

    def test_generation_execute_runs_stitch_and_style(self):
        config = PipelineConfig.dry_run(self.tmpdir)
        orchestrator = NovelOrchestrator(config)
        orchestrator.stitch_editor = MagicMock()
        orchestrator.stitch_editor.edit_scenes.return_value = "缝合后的正文，林澈推开了门。"
        orchestrator.style_editor = MagicMock()
        orchestrator.style_editor.edit.return_value = "润色后的正文，林澈推开了门，雨水滴在地上。"
        phase = GenerationPhase(orchestrator)
        ctx = ChapterContext(
            chapter_id="001",
            chapter_goal="雨夜",
            chapter_dir=self.tmpdir / "chapter_001",
            scenes_dir=self.tmpdir / "chapter_001" / "scenes",
            reports_dir=self.tmpdir / "chapter_001" / "reports",
            plan={
                "scenes": [
                    {"scene_id": "001-01"},
                    {"scene_id": "001-02"},
                ]
            },
        )
        ctx.chapter_dir.mkdir(parents=True)
        ctx.scenes_dir.mkdir(parents=True)
        ctx.reports_dir.mkdir(parents=True)
        (ctx.scenes_dir / "scene_001-01.txt").write_text("第一场。林澈推开门。", encoding="utf-8")
        (ctx.scenes_dir / "scene_001-02.txt").write_text("第二场。灯灭了。", encoding="utf-8")

        result = phase._complete_after_merge(ctx, "第一场。林澈推开门。\n\n第二场。灯灭了。")

        orchestrator.stitch_editor.edit_scenes.assert_called_once()
        orchestrator.style_editor.edit.assert_called()
        self.assertTrue(result.final_text)

    def test_length_fix_rejects_polluted_candidate(self):
        llm = MagicMock()
        llm.generate.return_value = "```\n短输出\n```"
        agent = LengthFixAgent(llm)
        original = "林澈握紧长剑，雨水顺着袖口滴在地上。" * 8
        adjusted = agent.adjust(original, [10, 20])
        self.assertEqual(adjusted, original)

    def test_rewrite_audit_failure_is_marked_error(self):
        report = build_audit_error(RuntimeError("provider down"), stage="rewrite_attempt_1")
        self.assertEqual(report["status"], "error")
        self.assertNotEqual(report.get("risk_level"), "低")
        from novel_agent.quality.audit_rewrite import audit_requires_rewrite

        self.assertFalse(audit_requires_rewrite(report))

    def test_hierarchical_summary_reads_chapters_range(self):
        workspace = self.tmpdir / "workspace"
        workspace.mkdir()
        (workspace / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "测试",
                    "macro_outline": [
                        {"arc_name": "第一卷", "chapters": "1-5", "goal": "开局"},
                        {"arc_name": "第二卷", "chapters": "6-12", "goal": "中盘"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        packed = assemble_hierarchical_context(self.tmpdir, "007")
        self.assertIn("第二卷", packed["level1_arc_summary"])
        self.assertIn("第一卷", packed["level1_arc_summary"])

    def test_read_chapter_plain_text_prefers_sqlite(self):
        store = SQLiteStateStore(self.tmpdir)
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("磁盘旧稿", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps({"chapter_title": "雨夜"}, ensure_ascii=False),
            encoding="utf-8",
        )
        store.create_manuscript_document(
            chapter_id="001",
            title="雨夜",
            content_json={"type": "doc", "content": []},
            plain_text="SQLite 新稿林澈推开门",
            markdown_text="SQLite 新稿林澈推开门",
            source="editor",
        )
        self.assertIn("SQLite 新稿", read_chapter_plain_text(self.tmpdir, "001", store=store))

    def test_legacy_schema_is_not_silently_altered(self):
        db_path = self.tmpdir / "data" / "novel.sqlite"
        db_path.parent.mkdir(parents=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("create table tasks (id text primary key, status text)")
            conn.execute("insert into tasks values ('t1', 'pending')")
        store = SQLiteStateStore(self.tmpdir)
        self.assertEqual(store.schema_state, SchemaState.LEGACY)
        with sqlite3.connect(db_path) as conn:
            columns = {row[1] for row in conn.execute("pragma table_info(tasks)").fetchall()}
        self.assertEqual(columns, {"id", "status"})
        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
            }
        self.assertNotIn("app_metadata", tables)

    def test_events_only_unversioned_database_is_legacy(self):
        db_path = self.tmpdir / "data" / "novel.sqlite"
        db_path.parent.mkdir(parents=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("create table events (id text primary key, summary text)")
        store = SQLiteStateStore(self.tmpdir)
        self.assertEqual(store.schema_state, SchemaState.LEGACY)
        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
            }
        self.assertEqual(tables, {"events"})

    def test_planner_rejects_unparseable_output(self):
        agent = PlannerAgent(StaticLLM({"planner": "这不是 JSON"}))
        with self.assertRaises(LLMResponseError):
            agent.create_plan("001", "雨夜开场")

    def test_chief_editor_rejects_unparseable_output(self):
        agent = ChiefEditorAgent(StaticLLM({"chief_editor": "不是大纲"}))
        with self.assertRaises(LLMResponseError):
            agent.plan_novel("雨夜", "都市", 20)

    def test_save_task_does_not_clobber_claimed_v2_status(self):
        store = SQLiteStateStore(self.tmpdir)
        created = store.task_repository.create_task(
            task_id="task-claimed",
            project_id="book-1",
            task_type=TaskType.CHAPTER,
            payload={"chapter_id": "001"},
        )
        claimed = store.task_repository.claim_task(created.id, lease_seconds=30)
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, TaskStatus.CLAIMED)
        store.save_task("task-claimed", "001", "goal", False, "pending")
        reloaded = store.task_repository.get_task("task-claimed")
        self.assertEqual(reloaded.status, TaskStatus.CLAIMED)
        self.assertTrue(reloaded.claim_token)

    def test_plugin_view_document_without_html_is_empty(self):
        from novel_agent.plugins.manager import PluginManager

        manager = PluginManager(self.tmpdir)
        with self.assertRaises(ValueError):
            manager.load_view_document("missing", "view", "sess_x")

    def test_plugin_project_id_rejects_path_traversal(self):
        manager = PluginManager(self.tmpdir)
        with self.assertRaises(ValueError):
            manager._resolve_project_dir("../secret")
        with self.assertRaises(ValueError):
            manager._resolve_project_dir("a/b")


if __name__ == "__main__":
    unittest.main()
