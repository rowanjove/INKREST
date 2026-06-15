import base64
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from novel_agent.state.sqlite_store import SQLiteStateStore
from web.preset_manager import PresetManager
from web.server import app as web_app
from web.tasks import TaskManager
import web.server as web_server
from main import _prepare_remote_access


class SecurityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-security-test-"))
        self.base_dir = self.tmpdir / "workspace"
        self.base_dir.mkdir()
        self.original_base = web_server.BASE_DIR
        self.original_active = web_server._active_project_id
        self.original_task_manager = web_server._task_manager
        self.original_project_manager = web_server.project_manager
        self.original_preset_manager = getattr(web_server, "preset_manager", None)
        web_server.BASE_DIR = self.base_dir
        web_server._active_project_id = None
        web_server._task_manager = None
        web_server.project_manager = web_server.ProjectManager(self.base_dir)

    def tearDown(self):
        web_server.BASE_DIR = self.original_base
        web_server._active_project_id = self.original_active
        web_server._task_manager = self.original_task_manager
        web_server.project_manager = self.original_project_manager
        if self.original_preset_manager is not None:
            web_server.preset_manager = self.original_preset_manager
        shutil.rmtree(self.tmpdir)

    def test_compose_preset_rejects_project_path_traversal(self):
        outside_dir = self.tmpdir / "outside"
        outside_dir.mkdir()
        web_server.preset_manager = PresetManager(self.original_base)
        client = TestClient(web_app)

        response = client.post(
            "/api/presets/compose",
            json={
                "channel": "general",
                "theme": "dushi",
                "project_id": "..\\outside",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse((outside_dir / "assets" / "writing_guide.md").exists())

    def test_feedback_route_reads_requested_project_store(self):
        first_dir = self.base_dir / "projects" / "first"
        second_dir = self.base_dir / "projects" / "second"
        first_store = SQLiteStateStore(first_dir)
        second_store = SQLiteStateStore(second_dir)
        first_store.save_reader_feedback("001", 0.91, 0.09, 10)
        second_store.save_reader_feedback("002", 0.12, 0.88, 20)
        web_server._active_project_id = "first"
        web_server._task_manager = TaskManager(first_dir)
        client = TestClient(web_app)

        response = client.get("/api/projects/second/feedback")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["chapter_id"] for item in response.json()], ["002"])

    def test_compare_versions_rejects_version_from_another_chapter(self):
        store = SQLiteStateStore(self.base_dir)
        first_id = store.save_chapter_version("001", "first", "first", "{}", True)
        second_id = store.save_chapter_version("002", "second", "second", "{}", True)
        web_server._task_manager = TaskManager(self.base_dir)
        client = TestClient(web_app)

        response = client.post(
            "/api/chapters/001/versions/compare",
            json={"version_id_a": first_id, "version_id_b": second_id},
        )

        self.assertEqual(response.status_code, 400)

    def test_import_zip_rejects_upload_larger_than_limit(self):
        client = TestClient(web_app)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project_info.json", json.dumps({"name": "large"}))

        with patch("web.routes.projects.MAX_PROJECT_ZIP_BYTES", 8, create=True):
            response = client.post(
                "/api/projects/import-zip",
                files={"file": ("large.zip", payload.getvalue(), "application/zip")},
            )

        self.assertEqual(response.status_code, 413)

    def test_import_zip_rejects_large_uncompressed_archive(self):
        client = TestClient(web_app)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("large.txt", "a" * 128)

        with patch("web.routes.projects.MAX_PROJECT_ZIP_UNCOMPRESSED_BYTES", 64, create=True):
            response = client.post(
                "/api/projects/import-zip",
                files={"file": ("large.zip", payload.getvalue(), "application/zip")},
            )

        self.assertEqual(response.status_code, 413)

    def test_import_zip_rejects_python_plugins(self):
        client = TestClient(web_app)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("plugins/evil.py", "raise RuntimeError('must not run')")

        response = client.post(
            "/api/projects/import-zip",
            files={"file": ("plugin.zip", payload.getvalue(), "application/zip")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("executable", response.json()["detail"].lower())

    def test_save_cover_rejects_payload_larger_than_limit(self):
        project_dir = self.base_dir / "projects" / "cover"
        project_dir.mkdir(parents=True)
        client = TestClient(web_app)
        cover = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"a" * 64).decode("ascii")

        with patch("web.routes.covers.MAX_COVER_BYTES", 16, create=True):
            response = client.post(
                "/api/projects/cover/save-cover",
                json={"cover": cover},
            )

        self.assertEqual(response.status_code, 413)
        self.assertFalse((project_dir / "cover.jpg").exists())

    def test_state_changing_request_requires_configured_access_token(self):
        client = TestClient(web_app)
        with patch.dict(os.environ, {"NOVEL_AGENT_ACCESS_TOKEN": "test-token"}):
            rejected = client.post("/api/pet/debug-log", json={"message": "blocked"})
            accepted = client.post(
                "/api/pet/debug-log",
                json={"message": "accepted"},
                headers={"X-Novel-Agent-Token": "test-token"},
            )
            health = client.get("/api/health")

        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(health.status_code, 200)

    def test_read_request_requires_configured_access_token(self):
        client = TestClient(web_app)
        with patch.dict(os.environ, {"NOVEL_AGENT_ACCESS_TOKEN": "test-token"}):
            rejected = client.get("/api/projects")
            accepted = client.get(
                "/api/projects",
                headers={"X-Novel-Agent-Token": "test-token"},
            )

        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(accepted.status_code, 200)

    def test_remote_binding_requires_explicit_opt_in(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "--allow-remote"):
                _prepare_remote_access("0.0.0.0", False)

    def test_remote_binding_generates_access_token(self):
        with patch.dict(os.environ, {}, clear=True):
            _prepare_remote_access("0.0.0.0", True)
            self.assertTrue(os.environ["NOVEL_AGENT_ACCESS_TOKEN"])

    def test_loopback_local_setup_returns_token(self):
        from web.security import (
            LOCAL_SETUP_HEADER,
            LOCAL_SETUP_HEADER_VALUE,
            bootstrap_loopback_access_token,
            ACCESS_TOKEN_ENV,
        )

        with patch.dict(
            os.environ,
            {
                "NOVEL_AGENT_DISABLE_LOCAL_TOKEN": "",
                "NOVEL_AGENT_HOST": "127.0.0.1",
            },
            clear=False,
        ):
            os.environ.pop(ACCESS_TOKEN_ENV, None)
            bootstrap_loopback_access_token(self.base_dir)
            client = TestClient(web_app)
            rejected = client.get("/api/auth/local-setup")
            response = client.get(
                "/api/auth/local-setup",
                headers={LOCAL_SETUP_HEADER: LOCAL_SETUP_HEADER_VALUE},
            )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("token"))

    def test_clear_database_requires_token_when_configured(self):
        store = SQLiteStateStore(self.base_dir)
        store.upsert_reader_promise(
            {
                "id": "RP_TOKEN",
                "title": "promise",
                "status": "open",
                "description": "",
                "chapter_id": "001",
            }
        )
        client = TestClient(web_app)
        with patch.dict(os.environ, {"NOVEL_AGENT_ACCESS_TOKEN": "clear-test-token-value!!"}):
            denied = client.post("/api/database/clear", json={"confirm": True})
            allowed = client.post(
                "/api/database/clear",
                json={"confirm": True},
                headers={"X-Novel-Agent-Token": "clear-test-token-value!!"},
            )
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)

    def test_local_model_setup_is_disabled_without_explicit_opt_in(self):
        from fastapi import HTTPException
        from web.routes.config import post_setup_local

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOVEL_AGENT_ALLOW_RUNTIME_INSTALL", None)
            with patch("web.routes.config.threading.Thread") as thread_cls:
                with self.assertRaises(HTTPException) as ctx:
                    post_setup_local()

        self.assertEqual(ctx.exception.status_code, 403)
        thread_cls.assert_not_called()

    def test_model_endpoint_allows_loopback_for_local_first_models(self):
        from web.security import validate_outbound_model_base_url

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOVEL_AGENT_ALLOW_PRIVATE_MODEL_ENDPOINTS", None)
            self.assertEqual(
                validate_outbound_model_base_url("http://127.0.0.1:11434/v1"),
                "http://127.0.0.1:11434/v1",
            )
            self.assertEqual(
                validate_outbound_model_base_url("http://localhost:1234/v1"),
                "http://localhost:1234/v1",
            )

    def test_model_endpoint_rejects_private_lan_endpoint(self):
        from web.security import validate_outbound_model_base_url

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOVEL_AGENT_ALLOW_PRIVATE_MODEL_ENDPOINTS", None)
            with self.assertRaisesRegex(ValueError, "private or local networks"):
                validate_outbound_model_base_url("http://192.168.1.20:9999/v1")

    def test_export_markdown_matches_requested_chapter_id_exactly(self):
        from web.routes.database import export_markdown_internal

        chapters_dir = self.base_dir / "workspace" / "chapters"
        for chapter_id, text in (
            ("001", "only chapter one"),
            ("011", "wrong chapter eleven"),
            ("101", "wrong chapter one hundred one"),
        ):
            chapter_dir = chapters_dir / f"chapter_{chapter_id}"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "chapter_final.txt").write_text(text, encoding="utf-8")

        output_path = self.tmpdir / "export.md"

        export_markdown_internal(
            self.base_dir,
            output_path,
            chapter_ids=["1"],
            title="Exact Export",
        )

        exported = output_path.read_text(encoding="utf-8")
        self.assertIn("only chapter one", exported)
        self.assertNotIn("wrong chapter eleven", exported)
        self.assertNotIn("wrong chapter one hundred one", exported)

    def test_export_markdown_raises_when_selection_has_no_chapters(self):
        from web.routes.database import export_markdown_internal

        chapter_dir = self.base_dir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("chapter one", encoding="utf-8")

        with self.assertRaises(ValueError):
            export_markdown_internal(
                self.base_dir,
                self.tmpdir / "empty.md",
                chapter_ids=["999"],
                title="Empty Export",
            )

    def test_websocket_rejects_query_string_token(self):
        from web.security import ACCESS_TOKEN_ENV, ACCESS_TOKEN_HEADER, websocket_has_access_token
        from unittest.mock import MagicMock

        ws = MagicMock()
        ws.headers = {}
        ws.query_params = {"access_token": "test-token-value-here!!!!"}

        with patch.dict(os.environ, {ACCESS_TOKEN_ENV: "test-token-value-here!!!!"}):
            self.assertFalse(websocket_has_access_token(ws))

        ws.headers = {ACCESS_TOKEN_HEADER: "test-token-value-here!!!!"}
        with patch.dict(os.environ, {ACCESS_TOKEN_ENV: "test-token-value-here!!!!"}):
            self.assertTrue(websocket_has_access_token(ws))

    def test_websocket_disconnect_during_auth_returns_false(self):
        import asyncio
        from starlette.websockets import WebSocketDisconnect
        from unittest.mock import AsyncMock, MagicMock
        from web.security import ACCESS_TOKEN_ENV, authorize_websocket

        ws = MagicMock()
        ws.headers = {}
        ws.query_params = {}
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect(1006))
        ws.close = AsyncMock()

        with patch.dict(os.environ, {ACCESS_TOKEN_ENV: "test-token-value-here!!!!"}):
            self.assertFalse(asyncio.run(authorize_websocket(ws)))

        ws.accept.assert_awaited_once()
        ws.close.assert_not_awaited()

    def test_token_compare_rejects_wrong_length_without_500(self):
        from web.security import _tokens_match

        self.assertFalse(_tokens_match("short", "much-longer-token-value"))
        self.assertTrue(_tokens_match("same-len-token-value-here!!", "same-len-token-value-here!!"))

    def test_lifespan_rejects_remote_without_token(self):
        from web.lifespan import lifespan
        from web.security import ALLOW_REMOTE_ENV, BIND_HOST_ENV, enforce_remote_auth_at_startup

        with patch.dict(
            os.environ,
            {BIND_HOST_ENV: "0.0.0.0", ALLOW_REMOTE_ENV: "1"},
            clear=False,
        ):
            os.environ.pop("NOVEL_AGENT_ACCESS_TOKEN", None)
            with self.assertRaises(RuntimeError):
                enforce_remote_auth_at_startup()

    def test_unhandled_exception_hides_internal_detail(self):
        import asyncio
        from unittest.mock import MagicMock

        from web.app import unhandled_exception_handler

        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/test"

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOVEL_AGENT_DEBUG", None)
            resp = asyncio.run(
                unhandled_exception_handler(
                    request, RuntimeError("secret-path C:\\users\\data")
                )
            )

        self.assertEqual(resp.status_code, 500)
        body = json.loads(resp.body)
        self.assertEqual(body["detail"], "服务器内部错误")
        self.assertNotIn("secret-path", body["detail"])

    def test_legacy_electron_export_routes_do_not_use_shell_command_strings(self):
        root = Path(__file__).resolve().parents[1]
        for rel in (
            "electron_version/electron/server/routes/export.ts",
            "web/frontend/electron/server/routes/export.ts",
        ):
            source = (root / rel).read_text(encoding="utf-8")
            self.assertNotIn("execSync(", source, rel)
            self.assertIn("spawnSync(", source, rel)
            self.assertIn("args = [", source, rel)

    def test_electron_runtime_sources_do_not_use_execsync_shell_strings(self):
        root = Path(__file__).resolve().parents[1]
        for rel in (
            "electron_version/electron",
            "web/frontend/electron",
        ):
            for path in (root / rel).rglob("*.ts"):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("execSync(", source, str(path.relative_to(root)))

    def test_import_zip_slip_traversal_denied(self):
        client = TestClient(web_app)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("../traversal_target.txt", "evil data")
        
        response = client.post(
            "/api/projects/import-zip",
            files={"file": ("traversal.zip", payload.getvalue(), "application/zip")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("traversal", response.json()["detail"].lower())
        
        outside_file = self.base_dir / "traversal_target.txt"
        parent_outside_file = self.base_dir.parent / "traversal_target.txt"
        self.assertFalse(outside_file.exists())
        self.assertFalse(parent_outside_file.exists())

    def test_db_write_lock_always_returns_result_in_async_context(self):
        import asyncio
        from novel_agent.state.sqlite_schema import db_write_lock
        
        class MockStore:
            def __init__(self, db_path):
                self.db_path = db_path
            
            @db_write_lock
            def write_something(self, val):
                return {"result": val}
        
        store = MockStore(self.base_dir / "test.db")
        store.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        async def call_in_loop():
            return store.write_something("hello")
        
        res = asyncio.run(call_in_loop())
        self.assertIsInstance(res, dict)
        self.assertEqual(res, {"result": "hello"})


if __name__ == "__main__":
    unittest.main()
