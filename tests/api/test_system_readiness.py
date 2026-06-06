"""System readiness API."""

from tests.api._base import *  # noqa: F403


class SystemReadinessApiTests(ApiTestBase):
    def test_system_readiness_returns_checks(self):
        client = TestClient(web_app)
        r = client.get("/api/system/readiness")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertIn("checks", data)
        self.assertIn("api", data["checks"])