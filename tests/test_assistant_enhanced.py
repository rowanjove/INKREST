import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

import web.server as web_server
from web.server import app as web_app
from web.tasks import TaskManager
from novel_agent.services.assistant_knowledge import (
    get_story_overview,
    get_character_snapshots,
    get_gate_diagnostic_detail,
    format_story_context_for_shanshan,
)
from novel_agent.services.assistant_diagnostics import (
    run_system_diagnostics,
    generate_offline_heuristic_reply,
)


class AssistantEnhancedTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-assistant-enhanced-"))
        import web.context as ws_context
        self.orig_base = ws_context.BASE_DIR
        ws_context.BASE_DIR = self.tmpdir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        import web.context as ws_context
        ws_context.BASE_DIR = self.orig_base

    def test_story_knowledge_extraction(self):
        root = self.tmpdir
        (root / "workspace").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "assets").mkdir(parents=True, exist_ok=True)

        (root / "workspace" / "outline.json").write_text(
            json.dumps({
                "chosen_title": "万界修仙纪元",
                "genre": "仙侠修真",
                "premise": "少年林云自微末崛起，以剑荡涤诸天万界。",
                "target_chapters": 100,
                "macro_outline": [
                    {"arc_id": "A01", "title": "青云入道", "goal": "拜入青云宗，夺得大比第一", "chapters": "1-20"},
                ],
            }),
            encoding="utf-8",
        )

        (root / "assets" / "character_cards.yaml").write_text(
            """characters:
  - id: protagonist
    name: 林云
    fixed_profile:
      role: 男主角
      core_motivation: 探寻身世真相，登临剑道绝巅
    personality_constraints:
      - 坚毅果决
      - 恩怨分明
""",
            encoding="utf-8",
        )

        ch1_reports = root / "workspace" / "chapters" / "chapter_001" / "reports"
        ch1_reports.mkdir(parents=True, exist_ok=True)
        (ch1_reports / "unified_gate.json").write_text(
            json.dumps({
                "overall_pass": False,
                "quality": {
                    "overall_score": 78,
                    "blocked_by": ["ai_smell_filter", "burstiness_guard"],
                    "rewrite_hints": "请削减【显而易见】、【仿佛】等AI特征高频词。",
                },
                "audit": {
                    "risk_level": "中等风险",
                    "issues": [
                        {"severity": "阻断", "message": "第1章包含多处空洞说明文字"},
                    ],
                },
            }),
            encoding="utf-8",
        )

        # 1. Test Story Overview
        overview = get_story_overview(root)
        self.assertEqual(overview["title"], "万界修仙纪元")
        self.assertEqual(overview["genre"], "仙侠修真")
        self.assertEqual(len(overview["macro_arcs"]), 1)
        self.assertEqual(overview["macro_arcs"][0]["arc_id"], "A01")

        # 2. Test Character Snapshots
        chars = get_character_snapshots(root)
        self.assertEqual(len(chars), 1)
        self.assertEqual(chars[0]["name"], "林云")
        self.assertEqual(chars[0]["role"], "男主角")
        self.assertIn("坚毅果决", chars[0]["personality"])

        # 3. Test Gate Details
        gate_detail = get_gate_diagnostic_detail(root, "001")
        self.assertIsNotNone(gate_detail)
        self.assertFalse(gate_detail["overall_pass"])
        self.assertEqual(gate_detail["score"], 78)
        self.assertIn("ai_smell_filter", gate_detail["blocked_by"])
        self.assertIn("削减", gate_detail["rewrite_hints"])

        # 4. Test formatted context string
        context_str = format_story_context_for_shanshan(root)
        self.assertIn("万界修仙纪元", context_str)
        self.assertIn("林云", context_str)
        self.assertIn("青云入道", context_str)

    def test_offline_heuristic_replies(self):
        root = self.tmpdir
        context_data = {
            "failed_tasks": [{"chapter_id": "003", "error": "质量守卫未通过", "gate_summary": "统一门禁：未通过；拦截项 ai_smell"}],
            "novel_batch": {"paused": True, "pause_reason": "连续三次门禁未过"},
        }

        # 1. Ask about failure
        resp1 = generate_offline_heuristic_reply("第3章为什么没过审？", root, context_data)
        self.assertIn("第 3 章", resp1["reply"])
        self.assertTrue(any(a["type"] == "navigate" for a in resp1["actions"]))
        self.assertTrue(len(resp1["suggestions"]) > 0)

        # 2. Ask about pause
        resp2 = generate_offline_heuristic_reply("全书暂停了，怎么续跑？", root, context_data)
        self.assertIn("暂停保护", resp2["reply"])
        self.assertIn("生产中心", resp2["reply"])

        # 3. Ask about models
        resp3 = generate_offline_heuristic_reply("日常档和逻辑档怎么配？", root, context_data)
        self.assertIn("日常档", resp3["reply"])
        self.assertIn("逻辑档", resp3["reply"])

    def test_diagnostics_retry_uses_resolved_chapter_goal(self):
        result = run_system_diagnostics(
            self.tmpdir,
            {"id": "project-1", "name": "测试项目"},
            [
                {
                    "task_id": "task-1",
                    "chapter_id": "001",
                    "status": "failed",
                    "error": "门禁未通过",
                }
            ],
            chapter_goal_resolver=lambda chapter_id: (
                "潜入王府取得密函" if chapter_id == "001" else None
            ),
        )

        retry = next(
            item for item in result["suggestions"] if item["type"] == "retry_task"
        )
        self.assertEqual(retry["payload"]["goal"], "潜入王府取得密函")

    def test_assistant_chat_streaming_endpoint(self):
        orig_base = web_server.BASE_DIR
        orig_active = web_server._active_project_id
        orig_manager = web_server._task_manager
        orig_project_manager = web_server.project_manager

        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("流式测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            web_server._task_manager = TaskManager(self.tmpdir / "projects" / project["id"])

            client = TestClient(web_app)
            
            # Stream with offline heuristics (since no real API key in test environment)
            response = client.post(
                "/api/assistant/chat/stream",
                json={"message": "这章为什么没过审？", "history": []},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers["content-type"])
            content = response.text
            self.assertIn("event: chunk", content)
            self.assertIn("event: done", content)
            self.assertIn("reply", content)

        finally:
            web_server.BASE_DIR = orig_base
            web_server._active_project_id = orig_active
            web_server._task_manager = orig_manager
            web_server.project_manager = orig_project_manager

    def test_inspect_gate_detail_fix_action(self):
        orig_base = web_server.BASE_DIR
        orig_active = web_server._active_project_id
        orig_manager = web_server._task_manager
        orig_project_manager = web_server.project_manager

        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("修复测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            root = self.tmpdir / "projects" / project["id"]
            web_server._task_manager = TaskManager(root)

            ch_reports = root / "workspace" / "chapters" / "chapter_005" / "reports"
            ch_reports.mkdir(parents=True, exist_ok=True)
            (ch_reports / "unified_gate.json").write_text(
                json.dumps({
                    "overall_pass": False,
                    "quality": {"overall_score": 82, "blocked_by": ["length_guard"]},
                    "audit": {"risk_level": "低", "issues": []},
                }),
                encoding="utf-8",
            )

            client = TestClient(web_app)
            response = client.post(
                "/api/assistant/fix",
                json={"fix_type": "inspect_gate_detail", "payload": {"chapter_id": "005"}},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["details"]["score"], 82)
            self.assertIn("length_guard", data["details"]["blocked_by"])

        finally:
            web_server.BASE_DIR = orig_base
            web_server._active_project_id = orig_active
            web_server._task_manager = orig_manager
            web_server.project_manager = orig_project_manager

    def test_assistant_chat_stream_prevents_marker_leak(self):
        from web.app import app
        from web.deps import ProjectSession
        import web.context as ws_server

        class MockLLM:
            async def astream(self, role, prompt):
                chunks = [
                    "山山在呢！当前作品状态良好。\n",
                    "请检查大纲设定。===",
                    "ACTIONS===\n[{\"type\": \"navigate\", \"payload\": {\"route\": \"/outline\"}}]",
                ]
                for c in chunks:
                    yield c

        from unittest.mock import patch
        client = TestClient(app)
        with patch("web.routes.assistant._get_assistant_llm", return_value=MockLLM()):
            resp = client.post(
                "/api/assistant/chat/stream",
                json={"message": "你好"},
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.text
            # Verify that no chunk event contains the marker ===ACTIONS===
            for line in body.splitlines():
                if line.startswith("data:") and '"chunk":' in line:
                    chunk_val = json.loads(line.replace("data: ", ""))["chunk"]
                    self.assertNotIn("===ACTIONS===", chunk_val)
                    self.assertNotIn("===", chunk_val)
            # Verify done event parsed the action
            self.assertIn('"actions"', body)
            self.assertIn('"/outline"', body)

