from tests.api._base import *  # noqa: F403

class ApiConfigTests(ApiTestBase):

    def test_config_schema_endpoint_exposes_v2_form_contract(self):
        response = TestClient(web_app).get("/api/config/schema")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["schema_version"], 2)
        self.assertIn("runtime", body["schema"]["properties"])

    def test_invalid_yaml_returns_structured_error_instead_of_defaults(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            config_dir = self.tmpdir / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "pipeline.yaml").write_text(
                "runtime: [broken",
                encoding="utf-8",
            )

            response = TestClient(web_app).get("/api/config")

            self.assertEqual(response.status_code, 422)
            body = response.json()
            self.assertEqual(body["code"], "CONFIG_INVALID")
            self.assertTrue(body["errors"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_update_config_returns_structured_error_for_invalid_existing_yaml(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            config_dir = self.tmpdir / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "pipeline.yaml").write_text(
                "runtime: [broken",
                encoding="utf-8",
            )

            response = TestClient(web_app).put(
                "/api/config",
                json={"runtime": {"max_workers": 2}},
            )

            self.assertEqual(response.status_code, 422)
            body = response.json()
            self.assertEqual(body["code"], "CONFIG_INVALID")
            self.assertEqual(body["errors"][0]["type"], "yaml_syntax")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_get_config_exposes_first_model_as_default_when_project_is_static(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            config_dir = self.tmpdir / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "pipeline.yaml").write_text(
                "llm:\n  provider: static\nruntime:\n  max_workers: 1\nembedding:\n  provider: stub\n",
                encoding="utf-8",
            )
            (config_dir / "models.json").write_text(
                json.dumps({
                    "models": {
                        "main-model": {
                            "provider": "openai",
                            "base_url": "http://localhost:11434/v1",
                            "api_key": "test",
                            "model": "qwen",
                        }
                    }
                }),
                encoding="utf-8",
            )

            config = web_server.get_config()

            self.assertEqual(config["llm"]["default_model_id"], "main-model")
            self.assertEqual(config["schema_name"], "pipeline_config")
            self.assertGreaterEqual(config["schema_version"], 1)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_update_config_does_not_mutate_sibling_project(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = "alpha"
            for pid, provider in (("alpha", "alpha-provider"), ("beta", "beta-provider")):
                config_path = self.tmpdir / "projects" / pid / "config" / "pipeline.yaml"
                config_path.parent.mkdir(parents=True)
                config_path.write_text(
                    f"llm:\n  provider: {provider}\nruntime:\n  max_workers: 1\n",
                    encoding="utf-8",
                )

            update_config(ConfigUpdate(llm={"provider": "new-provider"}))

            import yaml
            alpha = yaml.safe_load((self.tmpdir / "projects" / "alpha" / "config" / "pipeline.yaml").read_text(encoding="utf-8"))
            beta = yaml.safe_load((self.tmpdir / "projects" / "beta" / "config" / "pipeline.yaml").read_text(encoding="utf-8"))
            self.assertEqual(alpha["llm"]["provider"], "new-provider")
            self.assertEqual(beta["llm"]["provider"], "beta-provider")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_update_config_merges_partial_chapter_settings(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            config_path = self.tmpdir / "config" / "pipeline.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                yaml.dump(
                    {
                        "chapter": {
                            "default_target_chars": [1000, 2000],
                            "quality_mode": "report_only",
                        },
                        "runtime": {"max_workers": 2, "hook_fail_fast": False},
                    },
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            update_config(
                ConfigUpdate(
                    chapter={"quality_mode": "block_on_fail"},
                    runtime={"hook_fail_fast": True},
                )
            )

            saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["chapter"]["quality_mode"], "block_on_fail")
            self.assertEqual(saved["chapter"]["default_target_chars"], [1000, 2000])
            self.assertTrue(saved["runtime"]["hook_fail_fast"])
            self.assertEqual(saved["runtime"]["max_workers"], 2)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_embedding_status_reports_vector_semantic_flags(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "config").mkdir(parents=True, exist_ok=True)
            (self.tmpdir / "config" / "pipeline.yaml").write_text(
                "embedding:\n  provider: stub\n",
                encoding="utf-8",
            )
            ws = self.tmpdir / "workspace"
            ws.mkdir(parents=True, exist_ok=True)
            (ws / "outline.json").write_text(
                json.dumps({"scale_profile": {"scale": "medium", "vector_enabled": True}}),
                encoding="utf-8",
            )

            client = TestClient(web_app)
            resp = client.get("/api/config/embedding/status")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertTrue(body["vector_enabled"])
            self.assertFalse(body["semantic_search_effective"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_pipeline_alerts_skip_resolved_checkpoint(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_004"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "checkpoint.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "004",
                        "completed_stages": ["generation"],
                        "last_stage": "quality_blocked",
                        "resolved_at": "2026-06-02T20:00:00",
                    }
                ),
                encoding="utf-8",
            )
            resp = TestClient(web_app).get("/api/pipeline-alerts")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.json()["alerts"]), 0)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_pipeline_alerts_lists_quality_blocked_chapters(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_003"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "checkpoint.json").write_text(
                json.dumps(
                    {
                        "chapter_id": "003",
                        "completed_stages": ["generation"],
                        "last_stage": "quality_blocked",
                        "timestamp": "2026-06-02T12:00:00",
                    }
                ),
                encoding="utf-8",
            )
            reports = chapter_dir / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            (reports / "quality.json").write_text(
                json.dumps(
                    {
                        "mode": "block_on_fail",
                        "overall_pass": False,
                        "guard_summary": {
                            "overall_status": "FAIL",
                            "blocked_by": ["non_empty_final_text"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            resp = TestClient(web_app).get("/api/pipeline-alerts")
            self.assertEqual(resp.status_code, 200)
            alerts = resp.json()["alerts"]
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]["chapter_id"], "003")
            self.assertEqual(alerts[0]["last_stage"], "quality_blocked")
            self.assertIn("non_empty_final_text", alerts[0]["quality"]["blocked_by"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_model_library_seeds_deepseek_defaults_once(self):
        library = web_server.ModelLibrary(self.tmpdir)
        models = {model["id"]: model for model in library.list_models()}
        self.assertIn("deepseek-v4-flash", models)
        self.assertIn("deepseek-v4-pro", models)
        self.assertEqual(models["deepseek-v4-flash"]["name"], "DeepSeek V4 Flash")

    def test_model_library_restores_missing_pro_without_overwriting_existing_flash(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "deepseek-v4-flash": {
                            "name": "My Flash",
                            "provider": "openai",
                            "base_url": "https://example.test/v1",
                            "model": "custom-flash",
                        }
                    },
                    "defaults_seeded": True,
                }
            ),
            encoding="utf-8",
        )

        models = {model["id"]: model for model in web_server.ModelLibrary(self.tmpdir).list_models()}

        self.assertIn("deepseek-v4-pro", models)
        self.assertEqual(models["deepseek-v4-flash"]["name"], "My Flash")
        self.assertEqual(models["deepseek-v4-flash"]["model"], "custom-flash")

    def test_model_library_delete_clears_daily_and_reasoning_tier_references(self):
        config_dir = self.tmpdir / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "pipeline.yaml").write_text(
            "llm:\n"
            "  daily_model_id: daily\n"
            "  reasoning_model_id: pro\n"
            "  assistant:\n"
            "    model_ref: daily\n"
            "  overrides:\n"
            "    writer:\n"
            "      model_ref: daily\n",
            encoding="utf-8",
        )
        (config_dir / "models.json").write_text(
            json.dumps(
                {
                    "models": {
                        "daily": {"provider": "static", "model": "daily"},
                        "pro": {"provider": "static", "model": "pro"},
                    },
                    "defaults_seeded": True,
                }
            ),
            encoding="utf-8",
        )

        web_server.ModelLibrary(self.tmpdir).delete_model("daily")

        config = yaml.safe_load((config_dir / "pipeline.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("daily_model_id", config["llm"])
        self.assertNotIn("assistant", config["llm"])
        self.assertNotIn("writer", config["llm"]["overrides"])

    def test_novel_plan_request_accepts_epic_target_and_scale_label(self):
        req = NovelPlanRequest(theme="无限升级", genre="玄幻", target_chapters=1200, scale_label="几百上千章")
        self.assertEqual(req.target_chapters, 1200)
        self.assertEqual(req.scale_label, "几百上千章")

    def test_config_response_masks_api_keys(self):
        config = {
            "llm": {
                "default": {"provider": "openai", "api_key": "sk-live"},
                "overrides": {"writer": {"api_key": "sk-writer"}},
            },
            "embedding": {"provider": "openai", "api_key": "sk-embed"},
        }
        masked = _mask_config_secrets(config)

        self.assertEqual(masked["llm"]["default"]["api_key"], SECRET_MASK)
        self.assertEqual(masked["llm"]["overrides"]["writer"]["api_key"], SECRET_MASK)
        self.assertEqual(masked["embedding"]["api_key"], SECRET_MASK)
        self.assertEqual(config["llm"]["default"]["api_key"], "sk-live")

    def test_config_update_preserves_masked_api_keys(self):
        existing = {
            "default": {"provider": "openai", "api_key": "sk-old", "model": "old"},
        }
        incoming = {
            "default": {"provider": "openai", "api_key": SECRET_MASK, "model": "new"},
        }
        merged = _merge_preserving_masked_secrets(existing, incoming)

        self.assertEqual(merged["default"]["api_key"], "sk-old")
        self.assertEqual(merged["default"]["model"], "new")
