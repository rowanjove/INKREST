from datetime import datetime

from fastapi import HTTPException

from tests.api._base import *  # noqa: F403

class ApiProjectsTests(ApiTestBase):

    def test_delete_project_removes_only_target_directory_and_clears_active_context(self):
        import web.context as web_context

        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        original_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            target = web_server.ProjectManager(self.tmpdir).create_project("Delete me")
            target_dir = self.tmpdir / "projects" / target["id"]
            unrelated_dir = self.tmpdir / "projects" / "unregistered-neighbour"
            unrelated_dir.mkdir(parents=True)
            (unrelated_dir / "keep.txt").write_text("keep", encoding="utf-8")
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            web_server.activate_project(target["id"])

            response = TestClient(web_app).delete(f"/api/projects/{target['id']}")

            self.assertEqual(response.status_code, 200)
            self.assertFalse(target_dir.exists())
            self.assertTrue((unrelated_dir / "keep.txt").is_file())
            self.assertIsNone(web_context._active_project_id)
            registry = json.loads(
                (self.tmpdir / "projects.json").read_text(encoding="utf-8")
            )
            self.assertNotIn(target["id"], registry["projects"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base
            web_server.project_manager = original_manager

    def test_v2_maintenance_requires_exact_project_scoped_confirmation(self):
        original_base = web_server.BASE_DIR
        original_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            project_dir = self.tmpdir / "projects" / "safe-book"
            project_dir.mkdir(parents=True)
            registry = {
                "active_id": None,
                "projects": {"safe-book": {"name": "Safe Book"}},
            }
            (self.tmpdir / "projects.json").write_text(
                json.dumps(registry),
                encoding="utf-8",
            )
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            client = TestClient(web_app)

            backup = client.post(
                "/api/projects/safe-book/backup",
                json={"confirmation": "BACKUP wrong-book"},
            )
            reset = client.post(
                "/api/projects/safe-book/reset-v2",
                json={"confirmation": "RESET V2"},
            )

            self.assertEqual(backup.status_code, 400)
            self.assertEqual(reset.status_code, 400)
        finally:
            web_server.BASE_DIR = original_base
            web_server.project_manager = original_manager

    def test_v2_reset_api_rejects_persisted_active_task(self):
        original_base = web_server.BASE_DIR
        original_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            project_dir = self.tmpdir / "projects" / "busy-book"
            project_dir.mkdir(parents=True)
            (self.tmpdir / "projects.json").write_text(
                json.dumps(
                    {
                        "active_id": None,
                        "projects": {"busy-book": {"name": "Busy Book"}},
                    }
                ),
                encoding="utf-8",
            )
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            store = SQLiteStateStore(project_dir)
            store.task_repository.create_task(
                task_id="busy-task",
                project_id="busy-book",
                task_type="chapter",
                payload={"chapter_id": "001"},
            )
            client = TestClient(web_app)

            response = client.post(
                "/api/projects/busy-book/reset-v2",
                json={"confirmation": "RESET V2 busy-book"},
            )

            self.assertEqual(response.status_code, 409)
            self.assertTrue((project_dir / "data" / "novel.sqlite").is_file())
        finally:
            web_server.BASE_DIR = original_base
            web_server.project_manager = original_manager

    def test_plan_novel_preserves_existing_identity_unless_overwrite(self):
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
            outline_dir = self.tmpdir / "workspace"
            outline_dir.mkdir(parents=True)
            existing = {
                "title_options": ["《她与枪火》"],
                "core_theme": "电竞逆袭",
                "protagonist": {"name": "沈星璃", "desire": "夺冠"},
            }
            (outline_dir / "outline.json").write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
            generated = {
                "title_options": ["《新名字》"],
                "core_theme": "电竞逆袭",
                "protagonist": {"name": "林越", "desire": "冒险"},
                "macro_outline": [{"arc_id": "A01", "chapters": "1-20", "goal": "成长"}],
            }
            with patch("novel_agent.agents.base.StaticLLM.generate", return_value=json.dumps(generated, ensure_ascii=False)):
                result = web_server.plan_novel(NovelPlanRequest(theme="电竞逆袭", genre="电竞", target_chapters=20))

            self.assertEqual(result["title_options"], ["《她与枪火》"])
            self.assertEqual(result["protagonist"]["name"], "沈星璃")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_update_outline_saves_project_identity_fields(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            body = {
                "title_options": ["《枪声破晓》"],
                "core_theme": "电竞逆袭",
                "genre_positioning": "电竞",
                "protagonist": {"name": "沈星璃"},
            }

            result = web_server.update_outline(body)

            saved = json.loads((self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8"))
            self.assertEqual(result["protagonist"]["name"], "沈星璃")
            self.assertEqual(saved["title_options"], ["《枪声破晓》"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_update_author_label_persists_and_lists(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            pid = "author_label_proj"
            project_dir = self.tmpdir / "projects" / pid
            (project_dir / "config").mkdir(parents=True)
            (project_dir / "config" / "project_meta.json").write_text("{}", encoding="utf-8")
            registry = {
                "projects": {
                    pid: {
                        "name": "标签测试书",
                        "description": "",
                        "created_at": "2026-06-13T00:00:00",
                        "updated_at": "2026-06-13T00:00:00",
                    }
                },
                "active_id": pid,
            }
            (self.tmpdir / "projects.json").write_text(json.dumps(registry), encoding="utf-8")
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)

            client = TestClient(web_app)
            response = client.put(
                f"/api/projects/{pid}/author-label",
                json={"author_label": "夜雨笔名"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["author_label"], "夜雨笔名")

            meta = json.loads((project_dir / "config" / "project_meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["author_label"], "夜雨笔名")

            listed = client.get("/api/projects").json()
            matched = next(item for item in listed if item["id"] == pid)
            self.assertEqual(matched["author_label"], "夜雨笔名")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_rename_project_updates_registry_and_rejects_blank_name(self):
        original_base = web_server.BASE_DIR
        original_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "rename-book"
            (self.tmpdir / "projects" / pid).mkdir(parents=True)
            (self.tmpdir / "projects.json").write_text(
                json.dumps(
                    {
                        "active_id": pid,
                        "projects": {
                            pid: {
                                "name": "旧书名",
                                "created_at": "2026-07-01T00:00:00",
                                "updated_at": "2026-07-01T00:00:00",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            client = TestClient(web_app)

            response = client.patch(
                f"/api/projects/{pid}/name",
                json={"name": "  新书名  "},
            )
            blank = client.patch(
                f"/api/projects/{pid}/name",
                json={"name": "   "},
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], "新书名")
            self.assertEqual(blank.status_code, 400)
            listed = client.get("/api/projects").json()
            self.assertEqual(listed[0]["name"], "新书名")
        finally:
            web_server.BASE_DIR = original_base
            web_server.project_manager = original_manager

    def test_create_project_saves_resolved_scale_profile(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            result = web_server.create_project(web_server.ProjectCreateRequest(
                name="体量测试",
                target_chapters=1200,
                scale_label="几百上千章",
                outline={"title_options": ["《体量测试》"]},
            ))
            project_dir = self.tmpdir / "projects" / result["id"]
            meta = json.loads((project_dir / "config" / "project_meta.json").read_text(encoding="utf-8"))
            outline = json.loads((project_dir / "workspace" / "outline.json").read_text(encoding="utf-8"))

            self.assertEqual(meta["scale_profile"]["scale"], "epic")
            self.assertEqual(outline["scale_profile"]["scale"], "epic")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_dashboard_html_contains_chapter_report_summary(self):
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        reports_dir = chapter_dir / "reports"
        reports_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("最终正文", encoding="utf-8")
        (reports_dir / "wordcount.json").write_text(
            json.dumps({"count": 4, "status": "under"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (reports_dir / "audit.json").write_text(
            json.dumps({"risk_level": "低", "issues": [], "state_update": {}}, ensure_ascii=False),
            encoding="utf-8",
        )
        html_content = build_dashboard_html(self.tmpdir)
        self.assertIn("chapter_001", html_content)
        self.assertIn("低", html_content)
        self.assertIn("under", html_content)

    def test_dashboard_includes_foreshadows_and_characters(self):
        state_dir = self.tmpdir / "state"
        state_dir.mkdir()
        (state_dir / "foreshadows.yaml").write_text(
            "foreshadows:\n  - id: F001\n    title: 白塔医院\n    status: open\n    description: 神秘楼层\n",
            encoding="utf-8",
        )
        (state_dir / "continuity_state.yaml").write_text(
            "characters:\n  林澈:\n    location: 出租屋\n    emotion: 戒备\n    physical_state: 右手受伤\n",
            encoding="utf-8",
        )
        (state_dir / "hooks.yaml").write_text(
            "hooks:\n  - id: H001\n    title: 父亲声音\n    status: open\n    description: 门外传来\n",
            encoding="utf-8",
        )
        (state_dir / "objects.yaml").write_text(
            "objects:\n  - id: O001\n    name: 黑色录音笔\n    holder: 林澈\n    status: 损坏\n",
            encoding="utf-8",
        )
        (state_dir / "events.yaml").write_text(
            "events:\n  - id: E001\n    summary: 林澈遭遇停电\n",
            encoding="utf-8",
        )

        html_content = build_dashboard_html(self.tmpdir)
        self.assertIn("白塔医院", html_content)
        self.assertIn("林澈", html_content)
        self.assertIn("父亲声音", html_content)
        self.assertIn("黑色录音笔", html_content)
        self.assertIn("林澈遭遇停电", html_content)
        self.assertIn("伏笔状态", html_content)
        self.assertIn("人物状态", html_content)
        self.assertIn("道具归属", html_content)
        self.assertIn("事件时间线", html_content)

    def test_plan_novel_saves_scale_profile_metadata(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "config").mkdir(parents=True)
            (self.tmpdir / "config" / "pipeline.yaml").write_text(
                "llm:\n  provider: static\nruntime:\n  max_workers: 1\nembedding:\n  provider: stub\n",
                encoding="utf-8",
            )

            result = web_server.plan_novel(NovelPlanRequest(
                theme="无限升级",
                genre="玄幻",
                target_chapters=1200,
                scale_label="几百上千章",
            ))

            self.assertEqual(result["scale_profile"]["scale"], "epic")
            saved = json.loads((self.tmpdir / "workspace" / "outline.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["scale_profile"]["scale"], "epic")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_zip_export_and_import_lifecycle(self):
        import io
        import zipfile
        
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            pid = "dummy_proj"
            project_dir = self.tmpdir / "projects" / pid
            project_dir.mkdir(parents=True)
            (project_dir / "config").mkdir()
            (project_dir / "config" / "project_meta.json").write_text(json.dumps({"genre": "科幻"}), encoding="utf-8")
            (project_dir / "workspace").mkdir()
            (project_dir / "workspace" / "outline.json").write_text(json.dumps({"chosen_title": "测试包"}), encoding="utf-8")
            
            registry = {
                "projects": {
                    pid: {
                        "name": "测试包",
                        "description": "测试包描述",
                        "created_at": "2026-05-27T00:00:00",
                        "updated_at": "2026-05-27T00:00:00"
                    }
                },
                "active_id": pid
            }
            (self.tmpdir / "projects.json").write_text(json.dumps(registry), encoding="utf-8")
            
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)
            
            client = TestClient(web_app)
            
            export_resp = client.get(f"/api/projects/{pid}/export-zip")
            self.assertEqual(export_resp.status_code, 200)
            self.assertEqual(export_resp.headers.get("content-type"), "application/octet-stream")
            zip_bytes = export_resp.content
            
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                namelist = zf.namelist()
                self.assertIn("project_info.json", namelist)
                self.assertIn("config/project_meta.json", namelist)
                info = json.loads(zf.read("project_info.json").decode("utf-8"))
                self.assertEqual(info["name"], "测试包")
                self.assertEqual(info["description"], "测试包描述")
                
            import_resp = client.post(
                "/api/projects/import-zip",
                files={"file": ("project_export.zip", zip_bytes, "application/zip")}
            )
            self.assertEqual(import_resp.status_code, 200)
            res_json = import_resp.json()
            self.assertEqual(res_json["name"], "测试包")
            self.assertEqual(res_json["description"], "测试包描述")
            self.assertEqual(res_json["status"], "imported")
            
            new_pid = res_json["id"]
            new_registry = json.loads((self.tmpdir / "projects.json").read_text(encoding="utf-8"))
            self.assertIn(new_pid, new_registry["projects"])
            self.assertEqual(new_registry["projects"][new_pid]["name"], "测试包")
            
            self.assertTrue((self.tmpdir / "projects" / new_pid / "config" / "project_meta.json").exists())
            self.assertTrue((self.tmpdir / "projects" / new_pid / "workspace" / "outline.json").exists())
            
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_zip_import_preserves_pinned_metadata(self):
        import io
        import zipfile

        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        original_project_manager = web_server.project_manager
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)

            archive_buf = io.BytesIO()
            with zipfile.ZipFile(archive_buf, "w") as zf:
                zf.writestr(
                    "project_info.json",
                    json.dumps(
                        {
                            "name": "置顶导入",
                            "description": "imported pinned project",
                            "pinned": True,
                            "pinned_at": "2026-01-01T00:00:00",
                        },
                        ensure_ascii=False,
                    ),
                )
                zf.writestr("workspace/outline.json", json.dumps({"chosen_title": "置顶导入"}))

            response = TestClient(web_app).post(
                "/api/projects/import-zip",
                files={
                    "file": (
                        "pinned_project.zip",
                        archive_buf.getvalue(),
                        "application/zip",
                    )
                },
            )

            self.assertEqual(response.status_code, 200)
            pid = response.json()["id"]
            registry = json.loads((self.tmpdir / "projects.json").read_text(encoding="utf-8"))
            self.assertTrue(registry["projects"][pid]["pinned"])
            self.assertEqual(registry["projects"][pid]["pinned_at"], "2026-01-01T00:00:00")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base
            web_server.project_manager = original_project_manager

    def test_zip_export_excludes_executable_plugin_files(self):
        import io
        import zipfile

        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "safe_export"
            project_dir = self.tmpdir / "projects" / pid
            (project_dir / "plugins").mkdir(parents=True)
            (project_dir / "plugins" / "unsafe.py").write_text("raise RuntimeError('no')", encoding="utf-8")
            (project_dir / "workspace").mkdir()
            (project_dir / "workspace" / "notes.txt").write_text("safe", encoding="utf-8")
            (self.tmpdir / "projects.json").write_text(json.dumps({
                "projects": {pid: {"name": "safe", "description": ""}},
                "active_id": pid,
            }), encoding="utf-8")
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)

            response = TestClient(web_app).get(f"/api/projects/{pid}/export-zip")

            self.assertEqual(response.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                self.assertIn("workspace/notes.txt", archive.namelist())
                self.assertNotIn("plugins/unsafe.py", archive.namelist())
        finally:
            web_server.BASE_DIR = original_base

    def test_zip_export_excludes_local_secrets_and_logs(self):
        import io
        import zipfile

        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "secret_export"
            project_dir = self.tmpdir / "projects" / pid
            (project_dir / "workspace").mkdir(parents=True)
            (project_dir / "workspace" / "notes.txt").write_text("safe", encoding="utf-8")
            (project_dir / "config").mkdir()
            (project_dir / "config" / "pipeline.yaml").write_text(
                "api_key: leaked",
                encoding="utf-8",
            )
            (project_dir / "config" / "models.json").write_text(
                '{"api_key":"leaked"}',
                encoding="utf-8",
            )
            (project_dir / ".env.local").write_text("TOKEN=leaked", encoding="utf-8")
            (project_dir / "logs").mkdir()
            (project_dir / "logs" / "novel_agent.log").write_text(
                "private",
                encoding="utf-8",
            )
            (self.tmpdir / "projects.json").write_text(
                json.dumps(
                    {
                        "projects": {pid: {"name": "safe", "description": ""}},
                        "active_id": pid,
                    }
                ),
                encoding="utf-8",
            )
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)

            response = TestClient(web_app).get(f"/api/projects/{pid}/export-zip")

            self.assertEqual(response.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                names = set(archive.namelist())
                self.assertIn("workspace/notes.txt", names)
                self.assertNotIn("config/pipeline.yaml", names)
                self.assertNotIn("config/models.json", names)
                self.assertNotIn(".env.local", names)
                self.assertNotIn("logs/novel_agent.log", names)
        finally:
            web_server.BASE_DIR = original_base

    def test_zip_export_excludes_symlinks_to_files_outside_project(self):
        import io
        import zipfile

        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "safe_symlink_export"
            project_dir = self.tmpdir / "projects" / pid
            workspace_dir = project_dir / "workspace"
            workspace_dir.mkdir(parents=True)
            outside = self.tmpdir / "outside-secret.txt"
            outside.write_text("must not leak", encoding="utf-8")
            link = workspace_dir / "linked-secret.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"Symbolic links are unavailable: {exc}")
            (self.tmpdir / "projects.json").write_text(json.dumps({
                "projects": {pid: {"name": "safe", "description": ""}},
                "active_id": pid,
            }), encoding="utf-8")
            web_server.project_manager = web_server.ProjectManager(self.tmpdir)

            response = TestClient(web_app).get(f"/api/projects/{pid}/export-zip")

            self.assertEqual(response.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                self.assertNotIn("workspace/linked-secret.txt", archive.namelist())
        finally:
            web_server.BASE_DIR = original_base

    def test_project_list_sort_pinned_and_activity(self):
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            manager = web_server.ProjectManager(self.tmpdir)
            now = datetime.now()
            base_ts = now.timestamp()

            def make(pid, name, pinned=False, pinned_at="", updated_at=""):
                d = self.tmpdir / "projects" / pid
                (d / "workspace" / "chapters").mkdir(parents=True, exist_ok=True)
                reg = manager._read_registry()
                reg.setdefault("projects", {})[pid] = {
                    "name": name,
                    "description": "",
                    "created_at": now.isoformat(),
                    "updated_at": updated_at or now.isoformat(),
                }
                if pinned:
                    reg["projects"][pid]["pinned"] = True
                    reg["projects"][pid]["pinned_at"] = pinned_at or now.isoformat()
                manager._write_registry(reg)

            old = datetime.fromtimestamp(base_ts - 86400 * 3).isoformat()
            recent = datetime.fromtimestamp(base_ts - 60).isoformat()
            make("a", "旧书", updated_at=old)
            make("b", "新书", updated_at=recent)
            make("c", "置顶书", pinned=True, pinned_at=datetime.fromtimestamp(base_ts - 3600).isoformat())

            projects = manager.list_projects()
            self.assertEqual([p["id"] for p in projects], ["c", "b", "a"])
            self.assertTrue(projects[0]["pinned"])
        finally:
            web_server.BASE_DIR = original_base

    def test_project_pin_limit(self):
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            manager = web_server.ProjectManager(self.tmpdir)
            web_server.project_manager = manager
            ids = []
            for i in range(11):
                ids.append(manager.create_project(f"书{i}")["id"])
            for pid in ids[:10]:
                manager.set_pinned(pid, True)
            with self.assertRaises(HTTPException):
                manager.set_pinned(ids[10], True)
            client = TestClient(web_app)
            resp = client.put(f"/api/projects/{ids[10]}/pin", json={"pinned": True})
            self.assertEqual(resp.status_code, 400)
        finally:
            web_server.BASE_DIR = original_base

    def test_project_list_includes_pending_alert_count(self):
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "pending_proj"
            project_dir = self.tmpdir / "projects" / pid
            project_dir.mkdir(parents=True)
            (project_dir / "workspace" / "chapters" / "chapter_002").mkdir(parents=True)
            (project_dir / "workspace" / "chapters" / "chapter_002" / "checkpoint.json").write_text(
                '{"chapter_id":"002","last_stage":"quality_blocked"}',
                encoding="utf-8",
            )
            (self.tmpdir / "projects.json").write_text(
                json.dumps({"projects": {pid: {"name": "待修", "description": ""}}, "active_id": pid}),
                encoding="utf-8",
            )
            manager = web_server.ProjectManager(self.tmpdir)
            projects = manager.list_projects()
            self.assertEqual(projects[0]["pending_alert_count"], 1)
            cache_path = project_dir / "workspace" / "reports" / "pending_alert_count.cache.json"
            self.assertTrue(cache_path.is_file())
        finally:
            web_server.BASE_DIR = original_base

    def test_project_list_recognizes_png_cover(self):
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            pid = "png_cover"
            project_dir = self.tmpdir / "projects" / pid
            project_dir.mkdir(parents=True)
            (project_dir / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (self.tmpdir / "projects.json").write_text(json.dumps({
                "projects": {pid: {"name": "cover", "description": ""}},
                "active_id": pid,
            }), encoding="utf-8")
            manager = web_server.ProjectManager(self.tmpdir)

            projects = manager.list_projects()

            self.assertTrue(projects[0]["has_cover"])
        finally:
            web_server.BASE_DIR = original_base

    def test_analyze_novel_intro(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            client = TestClient(web_app)
            
            # Mock LLM and config
            with patch("novel_agent.pipeline.PipelineConfig.from_config") as mock_from_config:
                mock_llm = MagicMock()
                mock_response = {
                    "name": "提炼书名",
                    "description": "提炼简介",
                    "genre": "科幻",
                    "context": {
                        "theme": "提炼主题",
                        "target_chapters": 50,
                        "target_chars": [3000, 5000],
                        "summary_card": {
                            "title_suggestions": ["建议1", "建议2"],
                            "logline": "一句话故事线",
                            "genre_positioning": "科幻机甲",
                            "target_reader": "大众",
                            "reader_promise": ["爽快"],
                            "tone": "热血"
                        },
                        "protagonist": {
                            "name": "张无忌",
                            "desire": "拯救世界",
                            "flaw": "优柔寡断",
                            "edge": "乾坤大挪移"
                        },
                        "world_rules": ["规则一"],
                        "antagonistic_forces": ["反派一"],
                        "conflict": "终极冲突"
                    }
                }
                mock_llm.generate.return_value = json.dumps(mock_response, ensure_ascii=False)
                mock_config = MagicMock()
                mock_config.get_llm.return_value = mock_llm
                mock_from_config.return_value = mock_config
                
                response = client.post(
                    "/api/novel/analyze-intro",
                    json={"text": "粘贴的一段构想文字大纲..."}
                )
                self.assertEqual(response.status_code, 200)
                res_json = response.json()
                self.assertEqual(res_json["name"], "提炼书名")
                self.assertEqual(res_json["description"], "提炼简介")
                self.assertEqual(res_json["genre"], "科幻")
                self.assertEqual(res_json["context"]["protagonist"]["name"], "张无忌")
                
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_import_to_terminology(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            client = TestClient(web_app)
            
            # 1. 创建两个自定义资产
            client.post("/api/assets", json={
                "name": "asset_a",
                "label": "名词A",
                "extension": "md",
                "content": "这是原始的旧内容"
            })
            client.post("/api/assets", json={
                "name": "asset_b",
                "label": "名词B",
                "extension": "md",
                "content": "内容B"
            })
            
            # 2. 执行导入
            import_payload = {
                "names": ["asset_a", "asset_b"]
            }
            res = client.post("/api/assets/import-to-terminology", json=import_payload)
            self.assertEqual(res.status_code, 200)
            
            # 3. 校验 terminology.md 内容
            term_file = self.tmpdir / "assets" / "terminology.md"
            self.assertTrue(term_file.exists())
            term_content = term_file.read_text(encoding="utf-8")
            self.assertIn("## 名词A", term_content)
            self.assertIn("## 名词B", term_content)
            self.assertIn("这是原始的旧内容", term_content)
            self.assertIn("内容B", term_content)
            
            # 4. 再次导入以验证幂等替换（同名覆盖）
            client.put("/api/assets/asset_a", json={
                "content": "这是修改后的全新文本"
            })
            res2 = client.post("/api/assets/import-to-terminology", json={"names": ["asset_a"]})
            self.assertEqual(res2.status_code, 200)
            
            term_content2 = term_file.read_text(encoding="utf-8")
            self.assertIn("这是修改后的全新文本", term_content2)
            self.assertNotIn("这是原始的旧内容", term_content2)


        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base



if __name__ == "__main__":
    unittest.main()
