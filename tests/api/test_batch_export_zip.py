import io
import json
import zipfile

from tests.api._base import *  # noqa: F403


class BatchExportZipTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "projects.json").write_text(
            json.dumps(
                {
                    "projects": {
                        "book01": {
                            "name": "导出测试书",
                            "description": "批量导出",
                            "created_at": "2026-01-01T00:00:00",
                            "updated_at": "2026-01-01T00:00:00",
                        }
                    },
                    "active_id": None,
                }
            ),
            encoding="utf-8",
        )
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)
        project_dir = self.tmpdir / "projects" / "book01"
        (project_dir / "workspace").mkdir(parents=True)
        (project_dir / "workspace" / "outline.json").write_text(
            json.dumps({"chosen_title": "导出测试书"}, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_batch_export_zip_returns_manifest_and_project_files(self):
        response = TestClient(web_app).post(
            "/api/projects/batch-export-zip",
            json={"project_ids": ["book01"]},
        )

        self.assertEqual(response.status_code, 200)
        content_type = response.headers.get("content-type", "")
        self.assertTrue(
            "zip" in content_type or "octet-stream" in content_type,
            msg=f"unexpected content-type: {content_type}",
        )

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = set(zf.namelist())
            self.assertIn("batch_export_manifest.json", names)
            self.assertIn("book01/project_info.json", names)
            manifest = json.loads(zf.read("batch_export_manifest.json").decode("utf-8"))
            self.assertEqual(manifest["project_ids"], ["book01"])
            self.assertEqual(manifest["count"], 1)

    def test_batch_export_zip_rejects_unknown_project(self):
        response = TestClient(web_app).post(
            "/api/projects/batch-export-zip",
            json={"project_ids": ["missing"]},
        )
        self.assertEqual(response.status_code, 404)