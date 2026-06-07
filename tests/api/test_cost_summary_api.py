"""API: novel cost summary."""

from tests.api._base import *  # noqa: F403


class CostSummaryApiTests(ApiTestBase):

    def test_cost_summary_empty_project(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "data").mkdir(parents=True, exist_ok=True)
            client = TestClient(web_app)
            resp = client.get("/api/novel/cost-summary")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertIn("persisted", body)
            self.assertEqual(body["persisted"]["call_count"], 0)
            self.assertEqual(body["recent_rounds"], [])
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active

    def test_cost_summary_reads_sqlite_and_jsonl(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            from novel_agent.state.sqlite_store import SQLiteStateStore

            store = SQLiteStateStore(self.tmpdir)
            store.log_llm_cost(
                call_id="call_a",
                model="gpt-test",
                input_tokens=100,
                output_tokens=50,
                input_cost=0.01,
                output_cost=0.02,
                project_id=self.tmpdir.name,
            )
            ws = self.tmpdir / "workspace"
            ws.mkdir(parents=True, exist_ok=True)
            (ws / "autopilot_rounds.jsonl").write_text(
                '{"round": 1, "tokens_used": 4200}\n',
                encoding="utf-8",
            )
            client = TestClient(web_app)
            resp = client.get("/api/novel/cost-summary")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["persisted"]["call_count"], 1)
            self.assertEqual(body["persisted"]["total_tokens"], 150)
            self.assertEqual(body["recent_rounds"][0]["tokens_used"], 4200)
        finally:
            web_server.BASE_DIR = original_base
            web_server._active_project_id = original_active