"""API smoke tests for /api/novel/readiness and /api/novel/continue guards."""

import json

from tests.api._base import *  # noqa: F403
from tests.helpers.seed_engine import seed_usable_daily_model

from novel_agent.services.arc_queue import record_novel_batch_paused
from novel_agent.services.outline_sync import mark_arcs_synced_with_outline


def _seed_ready_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: test-daily\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    seed_usable_daily_model(root, model_id="test-daily")
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 40, encoding="utf-8")
    outline = {
        "chosen_title": "冒烟测试书",
        "target_chapters": 20,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-10", "goal": "g"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps({"arc_id": "A01", "chapters": [{"chapter_id": "001", "goal": "a"}]}),
        encoding="utf-8",
    )
    mark_arcs_synced_with_outline(root)


class ApiNovelReadinessTests(ApiTestBase):

    def test_readiness_reports_pending_without_title(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            _seed_ready_project(self.tmpdir)
            outline = json.loads(
                (self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8")
            )
            outline.pop("chosen_title")
            (self.tmpdir / "workspace" / "outline.json").write_text(
                json.dumps(outline, ensure_ascii=False), encoding="utf-8"
            )
            resp = TestClient(web_app).get("/api/novel/readiness")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertFalse(body.get("ok"))
            ids = {p["id"] for p in body.get("pending") or []}
            self.assertIn("title", ids)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_readiness_ok_when_project_ready(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            _seed_ready_project(self.tmpdir)
            resp = TestClient(web_app).get("/api/novel/readiness")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertTrue(body.get("has_arcs"))
            self.assertFalse(body.get("arc_queue_stale", {}).get("stale"))
            self.assertIn("novel_batch", body)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_continue_rejects_when_not_ready(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            _seed_ready_project(self.tmpdir)
            outline = json.loads(
                (self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8")
            )
            outline.pop("chosen_title")
            (self.tmpdir / "workspace" / "outline.json").write_text(
                json.dumps(outline, ensure_ascii=False), encoding="utf-8"
            )
            resp = TestClient(web_app).post(
                "/api/novel/continue",
                json={"dry_run": True, "autopilot": True, "max_chapters": 0},
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("书名", resp.json().get("detail", ""))
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_continue_rejects_circuit_breaker_without_force_resume(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            _seed_ready_project(self.tmpdir)
            record_novel_batch_paused(
                self.tmpdir,
                reason="circuit_breaker",
                last_chapter="007",
                arc_id="A01",
                streak=3,
            )
            resp = TestClient(web_app).post(
                "/api/novel/continue",
                json={"dry_run": True, "autopilot": True, "max_chapters": 0},
            )
            self.assertEqual(resp.status_code, 400)
            detail = resp.json().get("detail", "")
            self.assertIn("熔断", detail)
            ok_resp = TestClient(web_app).post(
                "/api/novel/continue",
                json={
                    "dry_run": True,
                    "autopilot": True,
                    "max_chapters": 0,
                    "force_resume": True,
                },
            )
            self.assertIn(ok_resp.status_code, (200, 500))
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base