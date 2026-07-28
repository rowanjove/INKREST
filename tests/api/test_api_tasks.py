from tests.api._base import *  # noqa: F403

import web.context as web_context
from novel_agent.domain.tasks import TaskType
from novel_agent.state.sqlite_store import safe_connection
from web.project_task_registry import ProjectTaskRegistry
from web.models import TaskStatus

class ApiTasksTests(ApiTestBase):
    def test_task_status_exposes_lifecycle_metadata(self):
        status = TaskStatus(
            task_id="task-meta",
            status="failed",
            chapter_id="001",
            status_reason="startup_cleanup",
            resumable_from="writer",
            last_heartbeat="2026-06-15 10:00:00",
        )

        payload = status.model_dump()

        self.assertEqual(payload["status_reason"], "startup_cleanup")
        self.assertEqual(payload["resumable_from"], "writer")
        self.assertEqual(payload["last_heartbeat"], "2026-06-15 10:00:00")

    def test_task_failure_result_includes_retry_action_contract(self):
        from novel_agent.exceptions import LLMTimeoutError
        from web.task_failures import task_failure_result

        payload = task_failure_result(LLMTimeoutError("timeout"), resumable_from="auditor")

        self.assertEqual(payload["code"], "LLM_TIMEOUT")
        self.assertTrue(payload["retryable"])
        self.assertEqual(payload["user_action"], "retry_or_reduce_concurrency")
        self.assertEqual(payload["resumable_from"], "auditor")

    def test_pending_auto_resume_policy_only_allows_standard_single_chapters(self):
        from web.tasks import _is_auto_resumable_single_chapter_task

        self.assertTrue(
            _is_auto_resumable_single_chapter_task(
                {
                    "id": "task-1",
                    "chapter_id": "001",
                    "task_type": "chapter",
                    "mode": "standard",
                    "status": "pending",
                }
            )
        )

        blocked = [
            {"id": "batch-1", "chapter_id": "", "task_type": "chapter_batch", "status": "pending"},
            {"id": "gate-1", "chapter_id": "001", "task_type": "chapter", "mode": "gate_only", "status": "pending"},
            {"id": "novel-1", "chapter_id": "", "task_type": "novel_run", "status": "pending"},
            {"id": "arc-1", "chapter_id": "", "task_type": "arc_run", "status": "pending"},
            {"id": "missing-chapter", "chapter_id": "", "task_type": "chapter", "status": "pending"},
        ]
        for task in blocked:
            with self.subTest(task=task["id"]):
                self.assertFalse(_is_auto_resumable_single_chapter_task(task))

    def test_task_manager_rejects_duplicate_running_chapter(self):
        manager = TaskManager(self.tmpdir)
        manager._running_chapters["001"] = "task-a"

        import asyncio
        with self.assertRaises(ValueError):
            asyncio.run(manager.submit_chapter("001", "same chapter"))

    def test_task_manager_rejects_concurrent_duplicate_chapter_submissions(self):
        import asyncio
        import time

        manager = TaskManager(self.tmpdir)
        release = None

        def delayed_no_active_task(_chapter_id):
            time.sleep(0.05)
            return None

        async def hold_task(*_args):
            await release.wait()

        async def run_scenario():
            nonlocal release
            release = asyncio.Event()
            manager._get_active_chapter_tasks = delayed_no_active_task
            manager._run_chapter = hold_task
            results = await asyncio.gather(
                manager.submit_chapter("001", "first"),
                manager.submit_chapter("001", "second"),
                return_exceptions=True,
            )
            release.set()
            await asyncio.gather(*manager._running_tasks.values(), return_exceptions=True)
            return results

        results = asyncio.run(run_scenario())

        self.assertEqual(sum(isinstance(item, str) for item in results), 1)
        self.assertEqual(sum(isinstance(item, ValueError) for item in results), 1)

    def test_task_manager_reports_active_tasks(self):
        manager = TaskManager(self.tmpdir)
        manager._running_tasks["task-a"] = MagicMock()

        self.assertTrue(manager.has_active_tasks())

    def test_submit_batch_persists_parent_task_and_allows_abort(self):
        import asyncio

        manager = TaskManager(self.tmpdir)

        async def run_scenario():
            release = asyncio.Event()

            async def fake_run_batch(*_args):
                await release.wait()

            manager._run_batch = fake_run_batch
            batch_id = await manager.submit_batch(
                [{"chapter_id": "001", "goal": "first"}],
                dry_run=True,
            )
            task = await manager.get_task_async(batch_id)
            abort_result = await manager.abort_task(batch_id)
            release.set()
            await asyncio.gather(*manager._running_tasks.values(), return_exceptions=True)
            return batch_id, task, abort_result

        batch_id, task, abort_result = asyncio.run(run_scenario())

        self.assertIsNotNone(task)
        self.assertEqual(task["task_id"], batch_id)
        self.assertIsNone(task["chapter_id"])
        self.assertEqual(task["status"], "pending")
        self.assertTrue(abort_result)
        aborted = manager.get_task(batch_id)
        self.assertEqual(aborted["status"], "cancelled")
        self.assertEqual(aborted["status_reason"], "user_abort")

    def test_batch_failure_uses_structured_task_failure_payload(self):
        import asyncio

        manager = TaskManager(self.tmpdir)
        batch_id = "batch-fail-1"
        manager._create_task_record(
            batch_id,
            TaskType.CHAPTER_BATCH,
            {
                "chapters": [{"chapter_id": "001", "goal": "first"}],
                "goal": "批量生成 1 章",
                "dry_run": True,
            },
        )

        async def failing_batch(*_args, **_kwargs):
            raise RuntimeError("batch exploded")

        async def run_scenario():
            with patch("web.tasks.run_chapter_batch", failing_batch):
                await manager._run_batch(
                    batch_id,
                    [{"chapter_id": "001", "goal": "first"}],
                    dry_run=True,
                )

        asyncio.run(run_scenario())

        task = manager.get_task(batch_id)
        self.assertEqual(task["status"], "failed")
        self.assertIn("message", task["result"])
        self.assertIn("batch exploded", task["error"])

    def test_switch_project_allows_background_tasks_via_registry(self):
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        original_registry = web_context._task_registry
        try:
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            first = web_server.project_manager.create_project("first")
            second = web_server.project_manager.create_project("second")
            registry = ProjectTaskRegistry()
            web_context._task_registry = registry
            web_server._active_project_id = first["id"]
            web_server._task_manager = None
            manager_a = registry.get(self.tmpdir / "projects" / first["id"])
            manager_a._running_tasks["task-a"] = MagicMock()

            result = web_server.switch_project(second["id"])

            self.assertEqual(result.get("id"), second["id"])
            manager_b = registry.get(self.tmpdir / "projects" / second["id"])
            self.assertIsNot(manager_a, manager_b)
            self.assertTrue(registry.has_active_tasks(self.tmpdir / "projects" / first["id"]))
            self.assertFalse(registry.has_active_tasks(self.tmpdir / "projects" / second["id"]))
        finally:
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager
            web_context._task_registry = original_registry

    def test_delete_inactive_project_rejects_active_background_tasks(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        original_registry = web_context._task_registry
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            web_server._task_manager = None
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            first = web_server.project_manager.create_project("first")
            second = web_server.project_manager.create_project("second")
            registry = ProjectTaskRegistry()
            web_context._task_registry = registry
            web_server._active_project_id = second["id"]
            manager_a = registry.get(self.tmpdir / "projects" / first["id"])
            manager_a._running_tasks["task-a"] = MagicMock()

            response = TestClient(web_app).delete(f"/api/projects/{first['id']}")

            self.assertEqual(response.status_code, 409)
            self.assertTrue((self.tmpdir / "projects" / first["id"]).exists())
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager
            web_context._task_registry = original_registry

    def test_clear_database_removes_narrative_debt_tables(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            store = SQLiteStateStore(self.tmpdir)
            store.upsert_reader_promise({
                "id": "RP_CLEAR",
                "title": "promise",
                "status": "open",
                "description": "",
                "chapter_id": "001",
            })
            store.upsert_secret({
                "id": "SEC_CLEAR",
                "title": "secret",
                "status": "hidden",
                "description": "",
                "chapter_id": "001",
            })

            response = TestClient(web_app).post(
                "/api/database/clear",
                json={"confirm": True},
            )
            self.assertEqual(response.status_code, 200)

            self.assertEqual(store.list_reader_promises(), [])
            self.assertEqual(store.list_secrets(), [])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_task_manager_persistence_and_reload(self):
        # 1. Create a task manager
        manager = TaskManager(self.tmpdir)
        task_id = "test-task-1"
        
        # 2. Simulate a worker whose lease expired before process restart.
        manager._create_task_record(
            task_id,
            TaskType.CHAPTER,
            {
                "chapter_id": "001",
                "goal": "Goal 1",
                "dry_run": True,
                "mode": "standard",
            },
        )
        manager._update_task_status(task_id, "running")
        with safe_connection(manager.store.db_path) as conn:
            conn.execute(
                """
                update tasks
                set lease_expires_at = '2000-01-01T00:00:00+00:00'
                where id = ?
                """,
                (task_id,),
            )
            
        # 3. Instantiate a new TaskManager to reload tasks from disk
        reloaded_manager = TaskManager(self.tmpdir)
        task = reloaded_manager.get_task(task_id)
        
        self.assertIsNotNone(task)
        # Reloading active tasks should requeue them as pending
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["status_reason"], "lease_expired")
        
        # 4. Check that succeeded tasks remain terminal after reload.
        reloaded_manager._update_task_status(task_id, "running")
        reloaded_manager._update_task_status(task_id, "completed")
            
        reloaded_manager2 = TaskManager(self.tmpdir)
        task2 = reloaded_manager2.get_task(task_id)
        self.assertEqual(task2["status"], "succeeded")
