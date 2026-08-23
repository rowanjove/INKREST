from tests.api._base import *  # noqa: F403

from novel_agent.services.longform_synth import seed_synthetic_project


class ApiSearchTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        seed_synthetic_project(self.tmpdir, chapters=2, seed=4)
        pipeline = self.tmpdir / "config" / "pipeline.yaml"
        pipeline.write_text(
            "runtime:\n  longform_flags:\n    m2_hybrid_retrieval: true\n",
            encoding="utf-8",
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_search_status_rebuild_and_query(self):
        client = TestClient(web_app)
        status = client.get("/api/search/status")
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["enabled"])
        rebuilt = client.post("/api/search/rebuild-index")
        self.assertEqual(rebuilt.status_code, 200)
        self.assertFalse(rebuilt.json()["degraded"])
        response = client.get("/api/search", params={"query": "第1章"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["results"])
