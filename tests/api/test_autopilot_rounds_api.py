"""API: list autopilot round log."""

import json

from tests.api._base import *  # noqa: F403


class AutopilotRoundsApiTests(ApiTestBase):

    def test_list_autopilot_rounds_empty(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "workspace").mkdir(parents=True, exist_ok=True)
            client = TestClient(web_app)
            resp = client.get("/api/novel/autopilot-rounds")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body.get("total"), 0)
            self.assertEqual(body.get("rounds"), [])
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active

    def test_list_autopilot_rounds_reads_jsonl(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            ws = self.tmpdir / "workspace"
            ws.mkdir(parents=True, exist_ok=True)
            path = ws / "autopilot_rounds.jsonl"
            path.write_text(
                json.dumps({"round": 1, "chapters_completed": 2, "ts": "2026-06-06"}) + "\n",
                encoding="utf-8",
            )
            client = TestClient(web_app)
            resp = client.get("/api/novel/autopilot-rounds?limit=10")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body.get("total"), 1)
            self.assertEqual(body["rounds"][0]["round"], 1)
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active