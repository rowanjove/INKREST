"""Smoke: ensure-queue + continue preflight (no real LLM)."""

import json
from unittest.mock import AsyncMock, patch

from tests.api._base import *  # noqa: F403
from tests.helpers.seed_engine import seed_usable_daily_model

from novel_agent.services.outline_sync import mark_arcs_synced_with_outline


def _seed(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: smoke\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    seed_usable_daily_model(root, model_id="smoke")
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 40, encoding="utf-8")
    outline = {
        "chosen_title": "冒烟链",
        "target_chapters": 10,
        "macro_outline": [{"arc_id": "A01", "chapters": "1-5", "goal": "g"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    (root / "workspace" / "arc_A01.json").write_text(
        json.dumps(
            {
                "arc_id": "A01",
                "chapters": [{"chapter_id": "001", "goal": "a"}],
            }
        ),
        encoding="utf-8",
    )
    mark_arcs_synced_with_outline(root)


class NovelSmokeChainTests(ApiTestBase):

    def test_ensure_queue_then_continue_dry_run(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            import web.context as web_context

            web_context._task_manager = None
            _seed(self.tmpdir)
            client = TestClient(web_app)
            with patch(
                "novel_agent.services.rolling_planner.prepare_queue_for_run",
                new_callable=AsyncMock,
                return_value={"arcs_created": 0, "briefs_added": 0, "pending_briefs": 1},
            ):
                q = client.post("/api/novel/ensure-queue")
            self.assertIn(q.status_code, (200, 400), q.text)
            r = client.post(
                "/api/novel/continue",
                json={"dry_run": True, "autopilot": True, "max_chapters": 0, "force_resume": True},
            )
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn("task_id", r.json())
            b = client.get("/api/novel/batch-status")
            self.assertEqual(b.status_code, 200)
            self.assertIn("pending_total", b.json())
            self.assertIn("authoritative_progress_note", b.json())
        finally:
            web_context._task_manager = None
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base