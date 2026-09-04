import json
from pathlib import Path
from unittest.mock import patch

from tests.api._base import *  # noqa: F403
from novel_agent.domain.tasks import TaskType, TaskStatus


class ApiTaskControlTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            "llm:\n  daily_model_id: test-model\nruntime:\n  max_workers: 1\n",
            encoding="utf-8",
        )
        (self.tmpdir / "workspace").mkdir(parents=True, exist_ok=True)
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps({"chosen_title": "测试书", "target_chapters": 10}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.store = SQLiteStateStore(self.tmpdir)

    def test_api_tasks_routes_and_idempotency(self):
        manager = web_server._get_task_manager()
        repo = manager.task_repository

        # Create parent task
        parent = repo.create_task(
            task_id="p-task-1",
            project_id="default",
            task_type=TaskType.NOVEL_CONTINUE,
            payload={"max_chapters": 5},
        )
        # Create child task
        child = repo.create_task(
            task_id="c-task-1",
            project_id="default",
            task_type=TaskType.CHAPTER,
            payload={"chapter_id": "001"},
            parent_task_id="p-task-1",
        )
        repo.set_active_child_task("p-task-1", "c-task-1")

        client = TestClient(web_app)

        # 1. GET /api/tasks/{task_id}
        resp = client.get("/api/tasks/p-task-1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["task_id"], "p-task-1")

        # 2. POST /api/tasks/{task_id}/pause
        resp_pause = client.post("/api/tasks/p-task-1/pause")
        self.assertEqual(resp_pause.status_code, 200)
        self.assertEqual(resp_pause.json()["status"], "paused")

        # Repeat pause (idempotent)
        resp_pause_again = client.post("/api/tasks/p-task-1/pause")
        self.assertEqual(resp_pause_again.status_code, 200)
        self.assertEqual(resp_pause_again.json()["status"], "paused")

        # 3. POST /api/tasks/{task_id}/cancel (cascade cancellation)
        resp_cancel = client.post("/api/tasks/p-task-1/cancel")
        self.assertEqual(resp_cancel.status_code, 200)
        self.assertEqual(resp_cancel.json()["status"], "cancelled")

        # Child task should also be cancelled
        child_after = repo.get_task("c-task-1")
        self.assertEqual(child_after.status, TaskStatus.CANCELLED)

        # Repeat cancel (idempotent, does not error)
        resp_cancel_again = client.post("/api/tasks/p-task-1/cancel")
        self.assertEqual(resp_cancel_again.status_code, 200)
        self.assertEqual(resp_cancel_again.json()["status"], "cancelled")
