import json
import sqlite3
import tempfile
import unittest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection
from novel_agent.dashboard import build_dashboard_html
from web.tasks import TaskManager
import web.server as web_server
from web.models import ChapterPlanRequest, NovelPlanRequest
from web.models import ConfigUpdate
from web.routes.config import update_config
from web.server import SECRET_MASK, _delete_chapter_dir, _mask_config_secrets, _merge_preserving_masked_secrets
from web.server import app as web_app

__all__ = [
    "ApiTestBase",
    "TestClient",
    "web_app",
    "web_server",
    "SQLiteStateStore",
    "safe_connection",
    "TaskManager",
    "ChapterPlanRequest",
    "NovelPlanRequest",
    "ConfigUpdate",
    "update_config",
    "SECRET_MASK",
    "_delete_chapter_dir",
    "_mask_config_secrets",
    "_merge_preserving_masked_secrets",
    "build_dashboard_html",
    "json",
    "sqlite3",
    "tempfile",
    "unittest",
    "yaml",
    "Path",
    "MagicMock",
    "patch",
]


class ApiTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-api-test-"))
        import web.context as web_context

        # API routes still expose a legacy module shim, while the real state
        # lives in web.context. Snapshot both layers and clean any temporary
        # TaskManager/PluginManager instances before restoring them.
        self._api_original_state = {
            "base_dir": web_context.BASE_DIR,
            "active_project_id": web_context._active_project_id,
            "task_manager": web_context._task_manager,
            "task_registry": web_context._task_registry,
            "plugin_manager": web_context._plugin_manager,
            "global_plugin_manager": web_context._global_plugin_manager,
            "project_manager": web_server.project_manager,
        }
        # Scope all API requests to this case's temporary root. Several
        # tests intentionally only patch BASE_DIR; leaving the lazy manager
        # bound to the real checkout would write projects.json in the repo.
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)
        self.addCleanup(self._restore_api_state)

    def _restore_api_state(self):
        import web.context as web_context

        original = self._api_original_state
        tmp_root = self.tmpdir.resolve()

        def is_temp_manager(manager):
            try:
                return Path(manager.root_dir).resolve().is_relative_to(tmp_root)
            except (AttributeError, OSError, RuntimeError):
                return False

        registries = {web_context._task_registry, original["task_registry"]}
        for registry in registries:
            for key, manager in list(getattr(registry, "_managers", {}).items()):
                if is_temp_manager(manager):
                    try:
                        registry.drop(Path(key))
                    except Exception:
                        try:
                            manager.shutdown()
                        except Exception:
                            pass

        for manager in (
            web_context._task_manager,
            web_context._plugin_manager,
            web_context._global_plugin_manager,
        ):
            if manager is not None and manager not in original.values() and is_temp_manager(manager):
                try:
                    manager.shutdown()
                except Exception:
                    pass

        web_context.BASE_DIR = original["base_dir"]
        web_context._active_project_id = original["active_project_id"]
        web_context._task_manager = original["task_manager"]
        web_context._task_registry = original["task_registry"]
        web_context._plugin_manager = original["plugin_manager"]
        web_context._global_plugin_manager = original["global_plugin_manager"]
        web_server.BASE_DIR = original["base_dir"]
        web_server._active_project_id = original["active_project_id"]
        web_server._task_manager = original["task_manager"]
        web_server.project_manager = original["project_manager"]
        try:
            from web.runtime_log_buffer import clear_runtime_logs
            clear_runtime_logs()
        except Exception:
            pass

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir)

