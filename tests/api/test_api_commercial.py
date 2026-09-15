from tests.api._base import *  # noqa: F403


class ApiCommercialTests(ApiTestBase):

    def test_commercial_status_returns_valid_structure(self):
        client = TestClient(web_app)
        res = client.get("/api/commercial/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("license", data)
        self.assertIn("vault", data)
        self.assertIn("recovery", data)
        self.assertIn("budget", data)
        self.assertIn("tier", data["license"])
        self.assertIn("entitlements", data["license"])

    def test_activate_trial_license(self):
        client = TestClient(web_app)
        res = client.post("/api/commercial/license/trial")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "activated")
        self.assertEqual(data["tier"], "trial")
        self.assertEqual(data["license"]["payload"]["tier"], "trial")

    def test_health_check_endpoint(self):
        client = TestClient(web_app)
        res = client.post("/api/commercial/recovery/health-check")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn("issues", data)

    def test_budget_estimate_endpoint(self):
        client = TestClient(web_app)
        res = client.post(
            "/api/commercial/budget/estimate",
            json={"num_chapters": 5, "model": "deepseek-chat"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["num_chapters"], 5)
        self.assertGreater(data["total_tokens"], 0)
        self.assertGreater(data["estimated_cost_cny"], 0)
