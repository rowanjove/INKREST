from tests.api._base import *  # noqa: F403

from web.models import NovelContinueRequest, NovelPlanRequest


class ApiScaleLimitTests(ApiTestBase):
    def test_plan_request_epic_3001_is_rejected(self):
        with self.assertRaises(Exception) as exc:
            NovelPlanRequest(
                theme="测试",
                scale="epic",
                target_chapters=3001,
            )
        message = str(exc.exception)
        self.assertIn("3000", message)

    def test_plan_request_infinite_5000_is_accepted(self):
        req = NovelPlanRequest(
            theme="连载",
            scale="infinite",
            target_chapters=5000,
        )
        self.assertEqual(req.target_chapters, 5000)
        self.assertEqual(req.scale, "infinite")

    def test_continue_request_rejects_5000_run_budget(self):
        with self.assertRaises(Exception):
            NovelContinueRequest(max_chapters=5000)

    def test_continue_request_allows_autopilot_total_cap(self):
        req = NovelContinueRequest(max_chapters=5000, autopilot=True)
        self.assertEqual(req.max_chapters, 5000)
        self.assertTrue(req.autopilot)
