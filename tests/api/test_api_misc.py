from tests.api._base import *  # noqa: F403

class ApiMiscTests(ApiTestBase):

    def test_preset_components_route_is_not_shadowed_by_preset_id_route(self):
        client = TestClient(web_app)
        response = client.get("/api/presets/components", params={"type": "channels"})
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()}
        self.assertIn("general", ids)

    def test_dismiss_pipeline_alert_sets_resolved_at(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_005"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "checkpoint.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "005",
                        "last_stage": "quality_blocked",
                        "completed_stages": ["generation"],
                    }
                ),
                encoding="utf-8",
            )
            resp = TestClient(web_app).post("/api/pipeline-alerts/005/dismiss")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("resolved_at", resp.json())
            checkpoint = json.loads((chapter_dir / "checkpoint.json").read_text(encoding="utf-8"))
            self.assertTrue(checkpoint.get("resolved_at"))
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_get_scale_profile_returns_outline_profile_and_upgrade_pressure(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "workspace").mkdir(parents=True)
            (self.tmpdir / "workspace" / "outline.json").write_text(json.dumps({
                "scale_profile": {"scale": "short", "max_chapters": 20, "label": "几章"},
            }, ensure_ascii=False), encoding="utf-8")
            chapters_dir = self.tmpdir / "workspace" / "chapters"
            for i in range(1, 19):
                chapter_dir = chapters_dir / f"chapter_{i:03d}"
                chapter_dir.mkdir(parents=True)
                (chapter_dir / "chapter_final.txt").write_text("正文", encoding="utf-8")

            result = web_server.get_scale_profile()

            self.assertEqual(result["profile"]["scale"], "short")
            self.assertTrue(result["upgrade_pressure"]["should_prompt"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base
