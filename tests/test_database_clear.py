"""Tests for SQLite narrative clear via API and store."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from novel_agent.state.sqlite_store import SQLiteStateStore
import web.server as web_server
from web.server import app as web_app


class DatabaseClearTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-db-clear-"))
        self.original_base = web_server.BASE_DIR
        self.original_active = web_server._active_project_id
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None

    def tearDown(self):
        web_server.BASE_DIR = self.original_base
        web_server._active_project_id = self.original_active
        shutil.rmtree(self.tmpdir)

    def test_clear_narrative_state_removes_vectors_and_debt(self):
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_reader_promise(
            {
                "id": "RP1",
                "title": "promise",
                "status": "open",
                "description": "",
                "chapter_id": "001",
            }
        )
        store.save_reader_feedback("001", 0.5, 0.5, 3)
        store.save_task("task-keep", "001", "goal", False, "running")
        self.assertEqual(len(store.list_reader_promises()), 1)

        cleared = store.clear_narrative_state()
        self.assertIn("reader_promises", cleared)
        self.assertEqual(store.list_reader_promises(), [])

        store2 = SQLiteStateStore(self.tmpdir)
        self.assertEqual(store2.list_reader_promises(), [])
        task = store2.get_task("task-keep")
        self.assertIsNotNone(task)

    def test_clear_database_api_requires_confirm(self):
        client = TestClient(web_app)
        denied = client.post("/api/database/clear", json={"confirm": False})
        self.assertEqual(denied.status_code, 400)

    def test_clear_database_api_uses_store_and_keeps_tasks_by_default(self):
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_secret(
            {
                "id": "SEC1",
                "title": "secret",
                "status": "hidden",
                "description": "",
                "chapter_id": "001",
            }
        )
        store.save_task("task-persist", "001", "goal", False, "running")
        client = TestClient(web_app)

        with patch.dict(os.environ, {"NOVEL_AGENT_DISABLE_LOCAL_TOKEN": "1"}, clear=False):
            response = client.post("/api/database/clear", json={"confirm": True})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "cleared")
        self.assertIn("secrets", payload.get("tables_cleared", {}))
        self.assertEqual(store.list_secrets(), [])
        self.assertIsNotNone(store.get_task("task-persist"))

    def test_local_setup_rejects_non_loopback_client(self):
        client = TestClient(web_app)
        with patch.dict(os.environ, {"NOVEL_AGENT_DISABLE_LOCAL_TOKEN": "1"}, clear=False):
            response = client.get(
                "/api/auth/local-setup",
                headers={"x-forwarded-for": "203.0.113.1"},
            )
        self.assertIn(response.status_code, (403, 503))