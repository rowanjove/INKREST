"""Per-project TaskManager registry."""

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


if __name__ == "__main__":
    unittest.main()