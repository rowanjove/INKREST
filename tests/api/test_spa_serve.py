import unittest
from pathlib import Path
from starlette.testclient import TestClient
import web.app as web_app


class TestSpaServe(unittest.TestCase):
    def test_root_serves_html(self):
        client = TestClient(web_app.app, raise_server_exceptions=False)
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<!doctype html>", r.text.lower())
        self.assertIn("<title>栖墨", r.text)

    def test_spa_subroute_fallback(self):
        client = TestClient(web_app.app, raise_server_exceptions=False)
        r = client.get("/workspace")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<!doctype html>", r.text.lower())

    def test_unmatched_api_returns_404_not_html(self):
        client = TestClient(web_app.app, raise_server_exceptions=False)
        r = client.get("/api/definitely_unknown_endpoint_xyz")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn("<!doctype html>", r.text.lower())
        data = r.json()
        self.assertIn("API endpoint not found", data.get("detail", ""))

    def test_unmatched_ws_returns_404_not_html(self):
        client = TestClient(web_app.app, raise_server_exceptions=False)
        r = client.get("/ws/definitely_unknown_ws")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn("<!doctype html>", r.text.lower())


if __name__ == "__main__":
    unittest.main()
