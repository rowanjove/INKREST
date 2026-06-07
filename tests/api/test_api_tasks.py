from tests.api._base import *  # noqa: F403

class ApiTasksTests(ApiTestBase):

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
        self.assertEqual(task["chapter_id"], "")
        self.assertEqual(task["status"], "pending")
        self.assertTrue(abort_result)
        self.assertEqual(manager.get_task(batch_id)["status"], "failed")

    def test_switch_project_rejects_when_active_tasks_are_running(self):
        original_active = web_server._active_project_id
        original_manager = web_server._task_manager
        original_project_manager = web_server.project_manager
        try:
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            first = web_server.project_manager.create_project("first")
            second = web_server.project_manager.create_project("second")
            web_server.project_manager.switch_project(first["id"])
            web_server._active_project_id = first["id"]
            manager = TaskManager(self.tmpdir / "projects" / first["id"])
            manager._running_tasks["task-a"] = MagicMock()
            web_server._task_manager = manager

            with self.assertRaises(Exception) as ctx:
                web_server.switch_project(second["id"])

            self.assertEqual(getattr(ctx.exception, "status_code", None), 409)
        finally:
            web_server._active_project_id = original_active
            web_server._task_manager = original_manager
            web_server.project_manager = original_project_manager

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
        
        # 2. Simulate task running state in DB and save
        manager.store.save_task(task_id, "001", "Goal 1", True, "running")
            
        # 3. Instantiate a new TaskManager to reload tasks from disk
        reloaded_manager = TaskManager(self.tmpdir)
        task = reloaded_manager.get_task(task_id)
        
        self.assertIsNotNone(task)
        # Reloading active tasks should mark them as failed with restart error
        self.assertEqual(task["status"], "failed")
        self.assertIn("服务重启", task["error"])
        
        # 4. Check that completed tasks are reloaded with original status
        manager.store.update_task_status(task_id, "completed", None, None)
            
        reloaded_manager2 = TaskManager(self.tmpdir)
        task2 = reloaded_manager2.get_task(task_id)
        self.assertEqual(task2["status"], "completed")
