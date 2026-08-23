from tests.api._base import *  # noqa: F403

from novel_agent.services.longform_synth import seed_synthetic_project


class ApiCatalogPaginationTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        seed_synthetic_project(self.tmpdir, chapters=15, seed=9)

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_manuscript_workspace_paginates_and_loads_selected_body(self):
        response = TestClient(web_app).get(
            "/api/manuscript/workspace",
            params={"offset": 10, "limit": 5, "chapter_id": "012"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["catalog_total"], 15)
        self.assertEqual(len(payload["chapters"]), 5)
        self.assertEqual(payload["chapters"][0]["chapter_id"], "011")
        self.assertEqual(payload["selected_chapter_id"], "012")
        self.assertIn("第12章", payload["document"]["plain_text"])
        self.assertNotIn("plain_text", payload["chapters"][0])

    def test_publishing_search_does_not_require_full_catalog(self):
        response = TestClient(web_app).get(
            "/api/publishing/workspace",
            params={"query": "第14章", "limit": 8},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["book"]["chapter_count"], 15)
        self.assertEqual(payload["catalog_total"], 1)
        self.assertEqual(payload["chapters"][0]["chapter_id"], "014")
        self.assertNotIn("plain_text", payload["chapters"][0])
        self.assertIn("第14章", payload["selected_chapter"]["plain_text"])

    def test_publishing_deep_link_returns_selected_page_and_global_index(self):
        seed_synthetic_project(self.tmpdir, chapters=5000, seed=9)
        response = TestClient(web_app).get(
            "/api/publishing/workspace",
            params={"chapter_id": "4999", "limit": 100},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["catalog_offset"], 4900)
        self.assertEqual(payload["selected_catalog_index"], 4998)
        self.assertEqual(payload["chapters"][0]["chapter_id"], "4901")
        self.assertEqual(payload["selected_chapter_id"], "4999")

    def test_non_numeric_chapter_id_is_rejected(self):
        response = TestClient(web_app).get(
            "/api/manuscript/workspace",
            params={"chapter_id": "../oops"},
        )
        self.assertEqual(response.status_code, 400)
