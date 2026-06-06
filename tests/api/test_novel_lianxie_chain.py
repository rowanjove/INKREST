"""连写启动链路：对齐前端 refreshContext → ensure-queue → continue。"""

import json
from unittest.mock import AsyncMock, patch

from tests.api._base import *  # noqa: F403

from novel_agent.services.outline_sync import mark_arcs_synced_with_outline


def _seed_ready(root: Path, *, with_arcs: bool = True, pending_briefs: int = 16) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: test-daily\n  reasoning_model_id: test-daily\nruntime:\n  max_workers: 1\n",
        encoding="utf-8",
    )
    (root / "config" / "models.json").write_text(
        json.dumps(
            {
                "models": {
                    "test-daily": {
                        "name": "Test Daily",
                        "provider": "openai",
                        "model": "gpt-test",
                    }
                },
                "slots": {"daily": "test-daily", "reasoning": "test-daily", "backup": []},
                "slots_version": 1,
                "defaults_seeded": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "assets").mkdir(exist_ok=True)
    for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
        (root / "assets" / name).write_text("x" * 40, encoding="utf-8")
    outline = {
        "chosen_title": "连写链路测试",
        "target_chapters": 10,
        "scale_profile": {"scale": "medium", "max_chapters": 10},
        "macro_outline": [{"arc_id": "A01", "chapters": "1-5", "goal": "g"}],
    }
    (root / "workspace").mkdir(exist_ok=True)
    (root / "workspace" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8"
    )
    if with_arcs:
        chapters = [
            {"chapter_id": f"{i:03d}", "goal": f"goal-{i}"}
            for i in range(1, pending_briefs + 1)
        ]
        (root / "workspace" / "arc_A01.json").write_text(
            json.dumps({"arc_id": "A01", "chapters": chapters}, ensure_ascii=False),
            encoding="utf-8",
        )
        mark_arcs_synced_with_outline(root)


# 与 useNovelBatchRun.refreshContext 调用的接口一致
REFRESH_PATHS = (
    "/api/assets",
    "/api/chapters/count?sync=true",
    "/api/outline",
    "/api/models",
    "/api/config",
    "/api/config/embedding/status",
    "/api/novel/arc-progress",
    "/api/novel/batch-status",
)


class NovelLianxieChainTests(ApiTestBase):

    def _run_refresh_chain(self, client: TestClient) -> None:
        for path in REFRESH_PATHS:
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200, f"{path}: {resp.text}")

    def test_refresh_ensure_continue_dry_run(self):
        """已有卷队列：ensure-queue 应快速返回，continue 可提交任务。"""
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            import web.context as web_context

            web_context._task_manager = None
            _seed_ready(self.tmpdir, with_arcs=True)
            client = TestClient(web_app)

            self._run_refresh_chain(client)

            ready = client.get("/api/novel/readiness")
            self.assertEqual(ready.status_code, 200)
            self.assertTrue(ready.json().get("ok"), ready.json())

            q = client.post("/api/novel/ensure-queue")
            self.assertEqual(q.status_code, 200, q.text)
            self.assertEqual(q.json().get("status"), "ok")

            cont = client.post(
                "/api/novel/continue",
                json={
                    "resume": True,
                    "max_chapters": 5,
                    "dry_run": True,
                    "autopilot": True,
                    "full_book": True,
                },
            )
            self.assertEqual(cont.status_code, 200, cont.text)
            self.assertIn("task_id", cont.json())
        finally:
            web_context._task_manager = None
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_ensure_queue_cold_start_without_llm(self):
        """无 arc 文件时 ensure-queue 会拆卷；mock 主编避免真实 LLM。"""
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        fake_arc = {
            "arc_id": "A01",
            "arc_name": "卷一",
            "chapters": [{"chapter_id": "001", "goal": "mock"}],
        }
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            import web.context as web_context

            web_context._task_manager = None
            _seed_ready(self.tmpdir, with_arcs=False)
            client = TestClient(web_app)

            with patch(
                "novel_agent.agents.managing_editor.ManagingEditorAgent.asplit_chapters",
                new_callable=AsyncMock,
                return_value=fake_arc,
            ), patch(
                "novel_agent.services.rolling_planner.replenish_rolling_window",
                new_callable=AsyncMock,
                return_value=0,
            ):
                q = client.post("/api/novel/ensure-queue")
            self.assertEqual(q.status_code, 200, q.text)
            self.assertTrue((self.tmpdir / "workspace" / "arc_A01.json").is_file())

            cont = client.post(
                "/api/novel/continue",
                json={
                    "resume": True,
                    "max_chapters": 1,
                    "dry_run": True,
                    "autopilot": False,
                    "full_book": True,
                },
            )
            self.assertEqual(cont.status_code, 200, cont.text)
        finally:
            web_context._task_manager = None
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_refresh_ensure_continue_with_yaml_txt_assets(self):
        """生产环境资产为 rules.yaml + sensitive_words.txt 时不应被 readiness 拦住。"""
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            import web.context as web_context

            web_context._task_manager = None
            _seed_ready(self.tmpdir, with_arcs=True)
            (self.tmpdir / "assets" / "rules.md").unlink(missing_ok=True)
            (self.tmpdir / "assets" / "sensitive_words.md").unlink(missing_ok=True)
            (self.tmpdir / "assets" / "rules.yaml").write_text(
                "rules:\n  version: 1\n", encoding="utf-8"
            )
            (self.tmpdir / "assets" / "sensitive_words.txt").write_text(
                "词\n", encoding="utf-8"
            )
            client = TestClient(web_app)
            self._run_refresh_chain(client)
            ready = client.get("/api/novel/readiness")
            self.assertTrue(ready.json().get("ok"), ready.json())
            cont = client.post(
                "/api/novel/continue",
                json={
                    "resume": True,
                    "max_chapters": 1,
                    "dry_run": True,
                    "autopilot": True,
                    "full_book": True,
                },
            )
            self.assertEqual(cont.status_code, 200, cont.text)
        finally:
            web_context._task_manager = None
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_continue_409_when_batch_already_running(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            import web.context as web_context

            web_context._task_manager = None
            _seed_ready(self.tmpdir, with_arcs=True)
            client = TestClient(web_app)
            body = {
                "resume": True,
                "max_chapters": 1,
                "dry_run": True,
                "autopilot": True,
                "full_book": True,
            }
            tm = web_context._get_task_manager()
            with patch(
                "web.tasks_autopilot.active_novel_batch_task_id_helper",
                return_value="novel-auto-busy",
            ):
                resp = client.post("/api/novel/continue", json=body)
            self.assertEqual(resp.status_code, 409, resp.text)
            body = resp.json()
            text = " ".join(
                str(body.get(k) or "")
                for k in ("detail", "hint", "message", "code")
            )
            self.assertTrue(
                "已在运行" in text or body.get("code") == "NOVEL_BATCH_RUNNING",
                body,
            )
            self.assertIsNotNone(tm)
        finally:
            web_context._task_manager = None
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base