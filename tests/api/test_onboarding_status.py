import os
import shutil

from tests.api._base import *  # noqa: F403


class OnboardingStatusTests(ApiTestBase):
    def test_onboarding_status_reports_demo_available(self):
        response = TestClient(web_app).get("/api/system/onboarding")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("has_projects", body)
        self.assertIn("demo_available", body)
        self.assertEqual(body.get("demo_id"), "demo-factory-novel")
        self.assertIn(body.get("suggested_next"), {"import_demo", "configure_llm", "open_factory"})

    def test_onboarding_status_uses_packaged_template_assets(self):
        repo_root = Path(__file__).resolve().parents[2]
        template_root = self.tmpdir / "templates"
        demo_assets = template_root / "assets" / "demo_projects" / "demo-factory-novel"
        shutil.copytree(repo_root / "assets" / "demo_projects" / "demo-factory-novel", demo_assets)

        original_templates = os.environ.get("NOVEL_AGENT_TEMPLATES")
        os.environ["NOVEL_AGENT_TEMPLATES"] = str(template_root)
        try:
            response = TestClient(web_app).get("/api/system/onboarding")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json().get("demo_available"))
        finally:
            if original_templates is None:
                os.environ.pop("NOVEL_AGENT_TEMPLATES", None)
            else:
                os.environ["NOVEL_AGENT_TEMPLATES"] = original_templates