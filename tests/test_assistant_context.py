import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from web.tasks import TaskManager
import web.server as web_server
from web.server import app as web_app


class AssistantContextTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-assistant-test-"))
        import web.context as ws_context
        self.original_context_base = ws_context.BASE_DIR
        ws_context.BASE_DIR = self.tmpdir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)
        import web.context as ws_context
        ws_context.BASE_DIR = self.original_context_base

    def test_assistant_context_handles_empty_workspace(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            web_server._active_project_id = None
            web_server._task_manager = TaskManager(self.tmpdir)

            response = TestClient(web_app).get("/api/assistant/context")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["backend_health"], "ok")
            self.assertIsNone(data["active_project"])
            self.assertEqual(data["running_tasks"], [])
            self.assertEqual(data["failed_tasks"], [])
            self.assertEqual(data["recent_logs"], [])
            self.assertEqual(data["novel_batch"]["paused"], False)
            self.assertIn("work", data)
            self.assertEqual(data["work"]["chapters_written"], 0)
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_assistant_context_summarizes_active_project_and_tasks(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]

            manager = TaskManager(self.tmpdir / "projects" / project["id"])
            # Save active task to DB
            manager.store.save_task("task-running", "001", "写第一章", False, "running")
            manager.store.update_task_progress("task-running", {"step": "writer", "status": "running", "chapter_id": "001", "timestamp": 1})
            
            # Save failed task to DB
            manager.store.save_task("task-failed", "002", "写第二章", False, "failed")
            manager.store.update_task_status("task-failed", "failed", None, "LLM API 429 rate limit")
            
            web_server._task_manager = manager

            root = self.tmpdir / "projects" / project["id"]
            (root / "workspace").mkdir(parents=True, exist_ok=True)
            (root / "config").mkdir(parents=True, exist_ok=True)
            import json

            (root / "workspace" / "outline.json").write_text(
                json.dumps(
                    {
                        "target_chapters": 80,
                        "scale_profile": {"scale": "medium", "label": "中篇", "target_chapters": 80},
                        "macro_outline": [{"arc_id": "A01"}],
                    }
                ),
                encoding="utf-8",
            )
            reports = root / "workspace" / "chapters" / "chapter_002" / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            (reports / "unified_gate.json").write_text(
                json.dumps({"overall_pass": False, "quality": {"blocked_by": ["test_guard"]}}),
                encoding="utf-8",
            )

            response = TestClient(web_app).get("/api/assistant/context")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["active_project"], {"id": project["id"], "name": "测试项目"})
            self.assertEqual(data["work"]["scale"], "medium")
            self.assertTrue(data["work"]["has_macro_outline"])
            self.assertEqual(data["running_tasks"][0]["id"], "task-running")
            self.assertEqual(data["running_tasks"][0]["step"], "writer")
            self.assertEqual(data["failed_tasks"][0]["id"], "task-failed")
            self.assertIn("429", data["failed_tasks"][0]["error"])
            self.assertIn("gate_summary", data["failed_tasks"][0])
            self.assertIn("未通过", data["failed_tasks"][0]["gate_summary"])
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_assistant_context_reports_batch_paused(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("批量测试")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            web_server._task_manager = TaskManager(self.tmpdir / "projects" / project["id"])

            root = self.tmpdir / "projects" / project["id"]
            reports_dir = root / "workspace" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            import json

            (reports_dir / "novel_batch_progress.json").write_text(
                json.dumps(
                    {
                        "status": "paused",
                        "pause_reason": "circuit_breaker",
                        "last_arc_id": "A01",
                        "last_chapter_id": "012",
                        "fail_streak": 3,
                    }
                ),
                encoding="utf-8",
            )

            response = TestClient(web_app).get("/api/assistant/context")
            self.assertEqual(response.status_code, 200)
            batch = response.json()["novel_batch"]
            self.assertTrue(batch["paused"])
            self.assertEqual(batch["last_arc_id"], "A01")
            self.assertEqual(batch["fail_streak"], 3)
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_assistant_diagnose(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            
            # 1. 未选择项目时诊断
            web_server._active_project_id = None
            response = TestClient(web_app).get("/api/assistant/diagnose")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertTrue(any(i["code"] == "NO_ACTIVE_PROJECT" for i in data["issues"]))
            
            # 2. 选择项目但未配置模型
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            
            global_cfg = self.tmpdir / "config"
            global_cfg.mkdir(parents=True, exist_ok=True)
            (global_cfg / "pipeline.yaml").write_text("llm:\n  provider: ''\n", encoding="utf-8")
            (global_cfg / "models.json").write_text(
                '{"models": {}, "slots": {"daily": "", "reasoning": "", "backup": []}, "slots_version": 1}',
                encoding="utf-8",
            )

            config_dir = self.tmpdir / "projects" / project["id"] / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "pipeline.yaml").write_text("runtime:\n  max_workers: 1\n", encoding="utf-8")

            web_server._task_manager = TaskManager(self.tmpdir / "projects" / project["id"])

            response = TestClient(web_app).get("/api/assistant/diagnose")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "error")
            self.assertTrue(
                any(
                    i["code"] in ("MISSING_LLM_CONFIG", "STATIC_LLM_WARNING")
                    for i in data["issues"]
                ),
            )
            
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_assistant_chat_static_fallback(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        
        import web.routes.assistant as assistant_module
        original_get_llm = assistant_module._get_assistant_llm
        
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            
            config_dir = self.tmpdir / "projects" / project["id"] / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "pipeline.yaml").write_text("llm:\n  default:\n    provider: static", encoding="utf-8")
            
            web_server._task_manager = TaskManager(self.tmpdir / "projects" / project["id"])
            
            from unittest.mock import MagicMock, AsyncMock
            mock_llm = MagicMock()
            mock_llm.agenerate = AsyncMock(return_value="你好，请前去配置大模型以开始使用。")
            assistant_module._get_assistant_llm = MagicMock(return_value=mock_llm)
            
            payload = {
                "message": "你好，请帮我分析一下系统现状",
                "history": []
            }
            response = TestClient(web_app).post("/api/assistant/chat", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("配置", data["reply"])
            self.assertEqual(len(data["actions"]), 0) # 因为 agenerate 成功返回，没有抛错，解析出的 action 应该为 0（除非 mock 回答里有 ===ACTIONS===）
            
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager
            assistant_module._get_assistant_llm = original_get_llm

    def test_assistant_fix_test_model_does_not_import_from_chat_module(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        import web.routes.assistant as assistant_module
        original_get_llm = assistant_module._get_assistant_llm

        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            web_server._task_manager = TaskManager(self.tmpdir / "projects" / project["id"])

            from novel_agent.agents.base import OpenAILLM
            from unittest.mock import MagicMock

            stub_client = OpenAILLM(api_key="test", base_url="http://127.0.0.1:9")
            stub_client.test = MagicMock(
                return_value={
                    "success": True,
                    "latency_ms": 42,
                    "response_preview": "pong",
                }
            )
            assistant_module._get_assistant_llm = MagicMock(return_value=stub_client)

            response = TestClient(web_app).post(
                "/api/assistant/fix",
                json={"fix_type": "test_model", "payload": {}},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["details"]["latency_ms"], 42)
            self.assertNotIn("cannot import name", str(data))
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager
            assistant_module._get_assistant_llm = original_get_llm

    def test_assistant_fix_retry_task(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            
            manager = TaskManager(self.tmpdir / "projects" / project["id"])
            from unittest.mock import AsyncMock
            manager.submit_chapter = AsyncMock(return_value="task-mock-id")
            web_server._task_manager = manager
            
            payload = {
                "fix_type": "retry_task",
                "payload": {
                    "chapter_id": "001",
                    "goal": "第一章测试重试"
                }
            }
            response = TestClient(web_app).post("/api/assistant/fix", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["task_id"], "task-mock-id")
            
            manager.submit_chapter.assert_called_once_with(
                chapter_id="001",
                goal="第一章测试重试",
                dry_run=False
            )
            
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_assistant_fix_retry_task_missing_goal_fallback(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            
            manager = TaskManager(self.tmpdir / "projects" / project["id"])
            from unittest.mock import AsyncMock
            manager.submit_chapter = AsyncMock(return_value="task-mock-id-fallback")
            web_server._task_manager = manager
            
            # Request without 'goal', should trigger fallback to "重新生成第 001 章内容"
            payload = {
                "fix_type": "retry_task",
                "payload": {
                    "chapter_id": "001"
                }
            }
            response = TestClient(web_app).post("/api/assistant/fix", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["task_id"], "task-mock-id-fallback")
            
            manager.submit_chapter.assert_called_once_with(
                chapter_id="001",
                goal="重新生成第 001 章内容",
                dry_run=False
            )
            
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

    def test_inline_rewrite(self):
        import web.routes.assistant as assistant_module
        original_get_llm = assistant_module._get_assistant_llm
        try:
            from unittest.mock import MagicMock, AsyncMock
            mock_llm = MagicMock()
            mock_llm.agenerate = AsyncMock(return_value="这是被改写后的文字")
            assistant_module._get_assistant_llm = MagicMock(return_value=mock_llm)

            payload = {
                "text": "这是一段普通文字",
                "instruction": "润色",
                "chapter_id": "001",
                "goal": "测试"
            }
            response = TestClient(web_app).post("/api/assistant/inline-rewrite", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["rewritten_text"], "这是被改写后的文字")
        finally:
            assistant_module._get_assistant_llm = original_get_llm

    def test_inline_expand(self):
        import web.routes.assistant as assistant_module
        original_get_llm = assistant_module._get_assistant_llm
        try:
            from unittest.mock import MagicMock, AsyncMock
            mock_llm = MagicMock()
            mock_llm.agenerate = AsyncMock(return_value="这是被扩写出来的文字")
            assistant_module._get_assistant_llm = MagicMock(return_value=mock_llm)

            payload = {
                "before_text": "在很久很久以前，",
                "chapter_id": "001",
                "goal": "测试续写"
            }
            response = TestClient(web_app).post("/api/assistant/inline-expand", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["expanded_text"], "这是被扩写出来的文字")
        finally:
            assistant_module._get_assistant_llm = original_get_llm

    def test_extract_sync_assets(self):
        original_base = web_server.BASE_DIR
        original_active = web_server._active_project_id
        original_project_manager = web_server.project_manager
        
        import web.context as ws_context
        original_ctx_active = ws_context._active_project_id
        
        from unittest.mock import MagicMock, patch
        try:
            web_server.BASE_DIR = self.tmpdir
            ws_context.BASE_DIR = self.tmpdir
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            ws_context.project_manager = web_server.project_manager
            
            project = web_server.project_manager.create_project("测试项目")
            web_server.project_manager.switch_project(project["id"])
            web_server._active_project_id = project["id"]
            ws_context._active_project_id = project["id"]
            
            mock_llm = MagicMock()
            mock_llm.generate = MagicMock(return_value='[{"name": "zhang_san", "label": "张三", "type": "道具", "description": "主角的徒弟"}]')
            
            with patch('novel_agent.pipeline.PipelineConfig.from_config') as mock_from_config:
                mock_config = MagicMock()
                mock_config.get_llm = MagicMock(return_value=mock_llm)
                mock_from_config.return_value = mock_config
                
                payload = {
                    "chapter_text": "突然，张三冲了出来。"
                }
                response = TestClient(web_app).post("/api/assets/extract-sync", json=payload)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data["success"])
                self.assertEqual(len(data["synced"]), 1)
                self.assertEqual(data["synced"][0]["name"], "zhang_san")
                self.assertEqual(data["synced"][0]["status"], "created")
                
                asset_file = self.tmpdir / "projects" / project["id"] / "assets" / "custom" / "zhang_san.md"
                self.assertTrue(asset_file.exists())

                
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active
            web_server.project_manager = original_project_manager
            ws_context._active_project_id = original_ctx_active



if __name__ == "__main__":
    unittest.main()
