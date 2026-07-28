"""Global llm/embedding merge across projects."""

import json
import unittest
from pathlib import Path

import yaml

from novel_agent.pipeline import (
    load_pipeline_settings,
    load_project_pipeline_file,
    resolve_global_config_dir,
)


class PipelineGlobalSettingsTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(self._tmpdir()) / "repo"
        self.repo.mkdir(parents=True)
        (self.repo / "projects.json").write_text(json.dumps({"projects": {}}), encoding="utf-8")
        gcfg = self.repo / "config"
        gcfg.mkdir()
        (gcfg / "pipeline.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "daily_model_id": "global-daily",
                        "reasoning_model_id": "global-reason",
                    },
                    "embedding": {"provider": "zhipu", "model": "emb-v1"},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        self.project = self.repo / "projects" / "abc123"
        (self.project / "config").mkdir(parents=True)
        (self.project / "workspace").mkdir(parents=True)
        (self.project / "config" / "pipeline.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {"daily_model_id": "stale-per-book"},
                    "embedding": {"provider": "stub"},
                    "runtime": {"max_workers": 2},
                    "chapter": {"default_target_chars": [1000, 1500]},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    def _tmpdir(self):
        import tempfile

        return tempfile.mkdtemp(prefix="novel-global-pipeline-")

    def test_resolve_global_dir(self):
        self.assertEqual(resolve_global_config_dir(self.project), self.repo / "config")

    def test_project_inherits_global_llm_and_embedding(self):
        settings = load_pipeline_settings(self.project)
        self.assertEqual(settings["llm"]["daily_model_id"], "global-daily")
        self.assertEqual(settings["llm"]["reasoning_model_id"], "global-reason")
        self.assertEqual(settings["embedding"]["provider"], "zhipu")
        self.assertEqual(settings["runtime"]["max_workers"], 2)
        self.assertEqual(settings["chapter"]["default_target_chars"], [1000, 1500])

    def test_legacy_single_tree_still_works(self):
        legacy = Path(self._tmpdir()) / "legacy"
        (legacy / "config").mkdir(parents=True)
        (legacy / "config" / "pipeline.yaml").write_text(
            "llm:\n  daily_model_id: only-local\n",
            encoding="utf-8",
        )
        self.assertIsNone(resolve_global_config_dir(legacy))
        settings = load_pipeline_settings(legacy)
        self.assertEqual(settings["llm"]["daily_model_id"], "only-local")


class PipelineGlobalApiTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        import shutil
        from tests.api._base import ApiTestBase, TestClient, web_app, web_server
        import web.context as web_context

        self.ApiTestBase = ApiTestBase
        self.TestClient = TestClient
        self.web_app = web_app
        self.web_server = web_server
        self.web_context = web_context
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-global-api-"))
        self.repo = self.tmpdir
        (self.repo / "projects.json").write_text(json.dumps({"projects": {}}), encoding="utf-8")
        (self.repo / "config").mkdir(exist_ok=True)
        (self.repo / "config" / "pipeline.yaml").write_text(
            "llm:\n  daily_model_id: before\nembedding:\n  provider: stub\n",
            encoding="utf-8",
        )
        pid = "p1"
        proj = self.repo / "projects" / pid
        for d in ("config", "workspace", "assets", "state", "prompts"):
            (proj / d).mkdir(parents=True, exist_ok=True)
        for name in ("world_bible.md", "style_guide.md", "rules.md", "sensitive_words.md"):
            (proj / "assets" / name).write_text("x" * 40, encoding="utf-8")
        (proj / "config" / "pipeline.yaml").write_text(
            "runtime:\n  max_workers: 3\n",
            encoding="utf-8",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_put_config_llm_writes_global_not_project(self):
        original_base = self.web_server.BASE_DIR
        original_active = self.web_server._active_project_id
        try:
            self.web_server.BASE_DIR = self.repo
            self.web_server._active_project_id = "p1"
            self.web_context._task_manager = None
            client = self.TestClient(self.web_app)
            resp = client.put(
                "/api/config",
                json={"llm": {"daily_model_id": "after-global", "reasoning_model_id": "r1"}},
            )
            self.assertEqual(resp.status_code, 200, resp.text)
            global_llm = yaml.safe_load(
                (self.repo / "config" / "pipeline.yaml").read_text(encoding="utf-8")
            )["llm"]
            self.assertEqual(global_llm["daily_model_id"], "after-global")
            proj_raw = yaml.safe_load(
                (self.repo / "projects" / "p1" / "config" / "pipeline.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("llm", proj_raw)
            merged = client.get("/api/config").json()
            self.assertEqual(merged["llm"]["daily_model_id"], "after-global")
        finally:
            self.web_context._task_manager = None
            self.web_server._active_project_id = original_active
            self.web_server.BASE_DIR = original_base


if __name__ == "__main__":
    unittest.main()