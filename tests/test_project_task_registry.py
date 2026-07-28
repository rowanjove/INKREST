"""Per-project TaskManager registry."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from web.project_task_registry import ProjectTaskRegistry
from web.tasks import TaskManager


class ProjectTaskRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="task-registry-"))
        self.project_a = self.tmpdir / "projects" / "alpha"
        self.project_b = self.tmpdir / "projects" / "beta"
        for path in (self.project_a, self.project_b):
            (path / "config").mkdir(parents=True)
            (path / "config" / "pipeline.yaml").write_text(
                "llm:\n  default:\n    provider: static\n",
                encoding="utf-8",
            )
            (path / "data").mkdir(parents=True)
        self.registry = ProjectTaskRegistry()

    def test_returns_distinct_managers_per_project(self):
        manager_a = self.registry.get(self.project_a)
        manager_b = self.registry.get(self.project_b)
        self.assertIsNot(manager_a, manager_b)
        self.assertEqual(self.registry.get(self.project_a), manager_a)

    def test_has_active_tasks_is_scoped_to_project(self):
        manager_a = self.registry.get(self.project_a)
        manager_a._running_tasks["task-a"] = MagicMock()
        self.assertTrue(self.registry.has_active_tasks(self.project_a))
        self.assertFalse(self.registry.has_active_tasks(self.project_b))

    def test_drop_removes_cached_manager(self):
        manager_a = self.registry.get(self.project_a)
        self.registry.drop(self.project_a)
        self.assertIsNot(self.registry.get(self.project_a), manager_a)

    def test_progress_handlers_are_isolated_between_concurrent_tasks(self):
        from novel_agent.progress import emit_progress, progress_handlers

        received_a = []
        received_b = []

        async def emit_for(label, received):
            with progress_handlers(
                received.append,
                lambda: False,
                project_id=f"project-{label}",
                task_id=f"task-{label}",
            ):
                await asyncio.sleep(0)
                emit_progress("writer", "running", {"owner": label}, "001")

        async def scenario():
            await asyncio.gather(
                emit_for("a", received_a),
                emit_for("b", received_b),
            )

        asyncio.run(scenario())

        self.assertEqual([message["data"]["owner"] for message in received_a], ["a"])
        self.assertEqual([message["data"]["owner"] for message in received_b], ["b"])
        self.assertEqual(received_a[0]["project_id"], "project-a")
        self.assertEqual(received_a[0]["task_id"], "task-a")
        self.assertEqual(received_b[0]["project_id"], "project-b")
        self.assertEqual(received_b[0]["task_id"], "task-b")

    def test_task_manager_construction_does_not_replace_default_progress_handler(self):
        from novel_agent.progress import emit_progress, register_progress_callback

        received = []
        register_progress_callback(received.append)
        try:
            self.registry.get(self.project_a)
            self.registry.get(self.project_b)

            emit_progress("writer", "running", {"owner": "cli"}, "001")
        finally:
            register_progress_callback(None)

        self.assertEqual([message["data"]["owner"] for message in received], ["cli"])


if __name__ == "__main__":
    unittest.main()
