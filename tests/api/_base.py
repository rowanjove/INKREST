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

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir)

