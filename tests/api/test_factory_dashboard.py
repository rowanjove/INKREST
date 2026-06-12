from tests.api._base import *  # noqa: F403


class FactoryDashboardTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_factory_dashboard_empty_without_project_workspace(self):
        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["factory_status"]["state"], "empty")
        self.assertEqual(body["production_plan"]["status"], "missing")
        for key in ("project", "production_plan", "factory_status", "pipeline", "repair", "exports"):
            self.assertIn(key, body)

    def test_factory_dashboard_summarizes_production_plan(self):
        workspace = self.tmpdir / "workspace"
        workspace.mkdir(parents=True)
        (workspace / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "星河试炼",
                    "selling_points": ["废柴逆袭", "星际学院"],
                    "target_chapters": 120,
                    "scale_profile": {"scale": "long"},
                    "chapters": [
                        {"chapter_id": "001", "goal": "入学"},
                        {"chapter_id": "002", "goal": "首战"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        chapter_dir = workspace / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("正文" * 80, encoding="utf-8")

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["production_plan"]["title"], "星河试炼")
        self.assertEqual(body["production_plan"]["target_chapters"], 120)
        self.assertEqual(body["production_plan"]["planned_chapters"], 2)
        self.assertEqual(body["factory_status"]["completed_chapters"], 1)
        self.assertIn(body["factory_status"]["state"], {"planning", "ready"})

    def test_factory_dashboard_surfaces_blocked_repair_item(self):
        workspace = self.tmpdir / "workspace"
        chapter_dir = workspace / "chapters" / "chapter_008"
        (chapter_dir / "reports").mkdir(parents=True)
        (workspace / "outline.json").write_text(
            json.dumps({"chosen_title": "门禁测试", "target_chapters": 20}, ensure_ascii=False),
            encoding="utf-8",
        )
        (chapter_dir / "checkpoint.json").write_text(
            json.dumps(
                {
                    "chapter_id": "008",
                    "last_stage": "quality_blocked",
                    "completed_stages": ["generation", "audit"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (chapter_dir / "plan.json").write_text(
            json.dumps({"chapter_title": "第八章", "chapter_goal": "修复测试"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (chapter_dir / "reports" / "quality.json").write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "guard_summary": {
                        "overall_status": "fail",
                        "blocked_by": ["ai_flavor", "continuity"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["factory_status"]["state"], "blocked")
        self.assertEqual(body["repair"]["blocked_count"], 1)
        item = body["repair"]["items"][0]
        self.assertEqual(item["chapter_id"], "008")
        self.assertIn(item["recommended_action"], {"auto_repair", "rerun_gate", "manual_edit"})
        self.assertTrue(item["manual_hint"])

    def test_factory_mode_update_persists_to_project_meta(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir(parents=True)

        response = TestClient(web_app).put(
            "/api/factory/mode",
            json={"mode": "platform_review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "platform_review")
        meta = json.loads((config_dir / "project_meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["factory_mode"], "platform_review")

        dashboard = TestClient(web_app).get("/api/factory/dashboard").json()
        self.assertEqual(dashboard["project"]["mode"], "platform_review")

    def test_factory_mode_update_rejects_unknown_mode(self):
        response = TestClient(web_app).put(
            "/api/factory/mode",
            json={"mode": "chaos_machine"},
        )

        self.assertEqual(response.status_code, 422)
