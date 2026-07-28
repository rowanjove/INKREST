from tests.api._base import *  # noqa: F403


class ApiProductionWorkspaceTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        (self.tmpdir / "config").mkdir(parents=True)
        (self.tmpdir / "config" / "pipeline.yaml").write_text(
            "schema_version: 2\n"
            "runtime:\n  max_workers: 1\n"
            "chapter:\n  default_target_chars: [1200, 2200]\n"
            "llm:\n  provider: static\n"
            "embedding:\n  provider: stub\n",
            encoding="utf-8",
        )
        (self.tmpdir / "workspace").mkdir()
        (self.tmpdir / "workspace" / "outline.json").write_text(
            json.dumps(
                {
                    "chosen_title": "API 生产中心",
                    "target_chapters": 10,
                    "macro_outline": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        store = SQLiteStateStore(self.tmpdir)
        store.task_repository.create_task(
            task_id="queued-1",
            project_id=self.tmpdir.name,
            task_type="chapter",
            payload={"chapter_id": "001"},
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_workspace_returns_one_canonical_production_contract(self):
        response = TestClient(web_app).get("/api/production/workspace")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["snapshot"]["project"]["id"], self.tmpdir.name)
        self.assertEqual(payload["tasks"][0]["id"], "queued-1")
        self.assertEqual(payload["tasks"][0]["status_label"], "等待中")
        self.assertNotIn("claim_token", payload["tasks"][0])
        self.assertIn("reviews", payload)
        self.assertIn("task_logs", payload)
