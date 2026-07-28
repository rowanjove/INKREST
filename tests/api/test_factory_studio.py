from tests.api._base import *  # noqa: F403


class FactoryStudioTests(ApiTestBase):
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

    def test_factory_studio_empty_registry(self):
        (self.tmpdir / "projects.json").write_text(
            json.dumps({"projects": {}, "active_id": None}),
            encoding="utf-8",
        )
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)

        response = TestClient(web_app).get("/api/factory/studio")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["total"], 0)
        self.assertIn("columns", body)
        self.assertIn("books_by_column", body)

    def test_factory_studio_groups_project_by_state(self):
        pid = "studio_book"
        project_dir = self.tmpdir / "projects" / pid
        (project_dir / "workspace").mkdir(parents=True)
        (project_dir / "assets").mkdir(parents=True)
        (project_dir / "config").mkdir(parents=True)
        (project_dir / "assets" / "character_cards.yaml").write_text("主角: 测试", encoding="utf-8")
        (project_dir / "assets" / "world_bible.md").write_text("世界观", encoding="utf-8")
        (project_dir / "assets" / "style_guide.md").write_text("风格", encoding="utf-8")
        (project_dir / "workspace" / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "工作室测试书",
                    "target_chapters": 20,
                    "chapters": [{"chapter_id": "001", "goal": "开篇"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        chapter_dir = project_dir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("正文" * 80, encoding="utf-8")

        registry = {
            "projects": {
                pid: {
                    "name": "工作室测试书",
                    "description": "",
                    "created_at": "2026-06-13T00:00:00",
                    "updated_at": "2026-06-13T00:00:00",
                }
            },
            "active_id": pid,
        }
        (self.tmpdir / "projects.json").write_text(json.dumps(registry), encoding="utf-8")
        web_server.project_manager = web_server.ProjectManager(self.tmpdir)
        web_server._active_project_id = pid

        response = TestClient(web_app).get("/api/factory/studio")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["total"], 1)
        self.assertEqual(body["books"][0]["name"], "工作室测试书")
        self.assertIn(body["books"][0]["factory_state"], {"ready", "planning", "running", "blocked", "complete"})