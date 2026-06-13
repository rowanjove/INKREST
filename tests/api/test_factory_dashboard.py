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
        for key in ("project", "production_plan", "factory_status", "mode_profile", "operator_brief", "commands", "pipeline", "repair", "exports"):
            self.assertIn(key, body)

    def test_factory_dashboard_summarizes_production_plan(self):
        workspace = self.tmpdir / "workspace"
        workspace.mkdir(parents=True)
        assets = self.tmpdir / "assets"
        assets.mkdir(parents=True)
        (assets / "character_cards.yaml").write_text("主角: 测试", encoding="utf-8")
        (assets / "world_bible.md").write_text("世界观测试", encoding="utf-8")
        (assets / "style_guide.md").write_text("风格测试", encoding="utf-8")
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

    def test_factory_dashboard_includes_mode_strategy_profile(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "project_meta.json").write_text(
            json.dumps({"factory_mode": "longform_stable"}, ensure_ascii=False),
            encoding="utf-8",
        )

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        profile = response.json()["mode_profile"]
        self.assertEqual(profile["mode"], "longform_stable")
        self.assertEqual(profile["label"], "长篇稳定")
        self.assertEqual(profile["automation_level"], "balanced")
        self.assertIn("设定连续性", profile["priorities"])
        self.assertTrue(profile["operator_hint"])

    def test_factory_mode_update_rejects_unknown_mode(self):
        response = TestClient(web_app).put(
            "/api/factory/mode",
            json={"mode": "chaos_machine"},
        )

        self.assertEqual(response.status_code, 422)

    def test_factory_dashboard_includes_mode_aware_commands(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "project_meta.json").write_text(
            json.dumps({"factory_mode": "platform_review"}, ensure_ascii=False),
            encoding="utf-8",
        )
        workspace = self.tmpdir / "workspace"
        workspace.mkdir(parents=True)
        assets = self.tmpdir / "assets"
        assets.mkdir(parents=True)
        (assets / "character_cards.yaml").write_text("主角: 测试", encoding="utf-8")
        (assets / "world_bible.md").write_text("世界观测试", encoding="utf-8")
        (assets / "style_guide.md").write_text("风格测试", encoding="utf-8")
        (workspace / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "过审测试",
                    "target_chapters": 20,
                    "chapters": [{"chapter_id": "001", "goal": "开场"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        commands = response.json()["commands"]
        command_ids = [item["id"] for item in commands]
        self.assertIn("export_risk_check", command_ids)
        self.assertIn("continue_production", command_ids)
        risk_command = next(item for item in commands if item["id"] == "export_risk_check")
        self.assertEqual(risk_command["intent"], "export")
        self.assertEqual(risk_command["tone"], "warning")
        self.assertTrue(risk_command["reason"])

    def test_factory_dashboard_includes_operator_brief_for_blocked_state(self):
        workspace = self.tmpdir / "workspace"
        chapter_dir = workspace / "chapters" / "chapter_009"
        (chapter_dir / "reports").mkdir(parents=True)
        (workspace / "outline.json").write_text(
            json.dumps({"chosen_title": "简报测试", "target_chapters": 30}, ensure_ascii=False),
            encoding="utf-8",
        )
        (chapter_dir / "checkpoint.json").write_text(
            json.dumps(
                {
                    "chapter_id": "009",
                    "last_stage": "quality_blocked",
                    "completed_stages": ["generation", "audit"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (chapter_dir / "reports" / "quality.json").write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "guard_summary": {
                        "overall_status": "fail",
                        "blocked_by": ["ai_flavor"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        brief = response.json()["operator_brief"]
        self.assertEqual(brief["severity"], "danger")
        self.assertEqual(brief["next_intent"], "repair")
        self.assertIn("009", brief["summary"])
        self.assertTrue(brief["details"])

    def test_factory_dashboard_includes_production_plan_next_steps(self):
        workspace = self.tmpdir / "workspace"
        workspace.mkdir(parents=True)
        (workspace / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "补齐指引测试",
                    "target_chapters": 60,
                    "chapters": [{"chapter_id": "001", "goal": "开场"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        response = TestClient(web_app).get("/api/factory/dashboard")

        self.assertEqual(response.status_code, 200)
        next_steps = response.json()["production_plan"]["next_steps"]
        step_ids = [item["id"] for item in next_steps]
        self.assertIn("character_cards", step_ids)
        self.assertIn("world_bible", step_ids)
        self.assertIn("style_guide", step_ids)
        first_step = next_steps[0]
        self.assertIn(first_step["intent"], {"plan", "asset"})
        self.assertTrue(first_step["label"])
        self.assertTrue(first_step["route"])
