import os
import shutil
from fastapi import HTTPException

from tests.api._base import *  # noqa: F403


class ImportDemoTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "projects.json").write_text(
            json.dumps({"projects": {}, "active_id": None}),
            encoding="utf-8",
        )
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_import_demo_project_creates_active_book(self):
        response = TestClient(web_app).post("/api/projects/import-demo")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "imported")
        self.assertEqual(body["demo_id"], "demo-factory-novel")
        self.assertIn(body["id"], web_server.project_manager._read_registry().get("projects", {}))
        self.assertTrue((self.tmpdir / "projects" / body["id"] / "workspace" / "outline.json").exists())
        chapters_root = self.tmpdir / "projects" / body["id"] / "workspace" / "chapters"
        self.assertEqual(len(list(chapters_root.glob("chapter_*/chapter_final.txt"))), 3)

    def test_import_demo_project_is_idempotent(self):
        client = TestClient(web_app)
        first = client.post("/api/projects/import-demo").json()
        second = client.post("/api/projects/import-demo").json()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["status"], "existing")

    def test_import_demo_project_uses_packaged_template_assets(self):
        repo_root = Path(__file__).resolve().parents[2]
        template_root = self.tmpdir / "templates"
        demo_assets = template_root / "assets" / "demo_projects" / "demo-factory-novel"
        shutil.copytree(repo_root / "assets" / "demo_projects" / "demo-factory-novel", demo_assets)

        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        original_templates = os.environ.get("NOVEL_AGENT_TEMPLATES")
        web_server.BASE_DIR = self.tmpdir / "workspace"
        web_server.BASE_DIR.mkdir(parents=True, exist_ok=True)
        web_server._active_project_id = None
        (web_server.BASE_DIR / "projects.json").write_text(
            json.dumps({"projects": {}, "active_id": None}),
            encoding="utf-8",
        )
        web_server.project_manager = web_server.ProjectManager(web_server.BASE_DIR)
        os.environ["NOVEL_AGENT_TEMPLATES"] = str(template_root)

        try:
            response = TestClient(web_app).post("/api/projects/import-demo")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["status"], "imported")
            self.assertEqual(body["demo_id"], "demo-factory-novel")
        finally:
            if original_templates is None:
                os.environ.pop("NOVEL_AGENT_TEMPLATES", None)
            else:
                os.environ["NOVEL_AGENT_TEMPLATES"] = original_templates
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_import_demo_project_blocks_when_current_project_has_running_tasks(self):
        active_dir = self.tmpdir / "projects" / "active"
        active_dir.mkdir(parents=True)
        (self.tmpdir / "projects.json").write_text(
            json.dumps({"projects": {"active": {"name": "Active"}}, "active_id": "active"}),
            encoding="utf-8",
        )
        web_server._active_project_id = "active"

        with patch("web.routes.projects.ws_server._ensure_no_active_tasks") as guard:
            guard.side_effect = HTTPException(409, "Tasks are running")
            response = TestClient(web_app).post("/api/projects/import-demo")

        self.assertEqual(response.status_code, 409)
        guard.assert_called_once_with("switch projects")
        data = web_server.project_manager._read_registry()
        self.assertEqual(data.get("active_id"), "active")
        self.assertEqual(list(data.get("projects", {}).keys()), ["active"])

    def test_import_demo_project_handles_empty_title_options(self):
        template_root = self.tmpdir / "templates-empty-title"
        demo_root = template_root / "assets" / "demo_projects" / "demo-factory-novel"
        (demo_root / "workspace").mkdir(parents=True)
        (demo_root / "config").mkdir(parents=True)
        (demo_root / "workspace" / "outline.json").write_text(
            json.dumps({"title_options": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        (demo_root / "config" / "project_meta.json").write_text(
            json.dumps({"is_demo": True, "demo_id": "demo-factory-novel"}),
            encoding="utf-8",
        )

        original_templates = os.environ.get("NOVEL_AGENT_TEMPLATES")
        os.environ["NOVEL_AGENT_TEMPLATES"] = str(template_root)
        try:
            response = TestClient(web_app).post("/api/projects/import-demo")
        finally:
            if original_templates is None:
                os.environ.pop("NOVEL_AGENT_TEMPLATES", None)
            else:
                os.environ["NOVEL_AGENT_TEMPLATES"] = original_templates

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "示例书")
