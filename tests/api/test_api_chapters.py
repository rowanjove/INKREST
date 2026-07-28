from tests.api._base import *  # noqa: F403

class ApiChaptersTests(ApiTestBase):

    def test_activate_version_snapshots_current_text_before_replacing_it(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "chapter_final.txt").write_text("旧正文", encoding="utf-8")
            (chapter_dir / "plan.json").write_text(
                json.dumps({"chapter_title": "第一章"}, ensure_ascii=False),
                encoding="utf-8",
            )
            store = SQLiteStateStore(self.tmpdir)
            version_id = store.save_chapter_version(
                chapter_id="001",
                version_name="新分支",
                content="新正文",
                plan="{}",
                is_active=False,
            )

            response = TestClient(web_app).post(
                f"/api/chapters/001/versions/{version_id}/activate"
            )

            self.assertEqual(response.status_code, 200)
            snapshots = list((chapter_dir / ".snapshots").glob("snapshot_*.json"))
            self.assertEqual(len(snapshots), 1)
            payload = json.loads(snapshots[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["final_text"], "旧正文")
            self.assertEqual(
                (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8"),
                "新正文",
            )
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_delete_chapter_dir_removes_only_requested_chapter(self):
        chapters_dir = self.tmpdir / "workspace" / "chapters"
        target = chapters_dir / "chapter_002"
        sibling = chapters_dir / "chapter_003"
        target.mkdir(parents=True)
        sibling.mkdir(parents=True)
        (target / "chapter_final.txt").write_text("chapter 2", encoding="utf-8")
        (sibling / "chapter_final.txt").write_text("chapter 3", encoding="utf-8")
        store = SQLiteStateStore(self.tmpdir)
        store.index_chapter("002", "第二章", target / "chapter_final.txt", 1200, "低")
        store.save_chapter_summary("002", "总结", target / "chapter_summary.md")

        deleted = _delete_chapter_dir(self.tmpdir, "002")

        self.assertEqual(deleted, target)
        self.assertFalse(target.exists())
        self.assertTrue(sibling.exists())
        conn = sqlite3.connect(self.tmpdir / "data" / "novel.sqlite")
        try:
            chapter_rows = conn.execute("select count(*) from chapters where id = '002'").fetchone()[0]
            summary_rows = conn.execute("select count(*) from chapter_summaries where chapter_id = '002'").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(chapter_rows, 0)
        self.assertEqual(summary_rows, 0)

    def test_delete_chapter_dir_removes_state_rows_for_chapter(self):
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_002"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("chapter 2", encoding="utf-8")
        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update("002", {
            "events": [{"id": "E002", "summary": "event"}],
            "timeline_nodes": [{"id": "N002", "name": "node"}],
            "timeline_edges": [{"id": "ED002", "from": "A", "to": "B"}],
            "foreshadows": [{"id": "F002", "title": "foreshadow"}],
            "hooks": [{"id": "H002", "title": "hook"}],
        })
        store.upsert_reader_promise({
            "id": "RP002",
            "title": "promise",
            "status": "open",
            "description": "",
            "chapter_id": "002",
        })
        store.upsert_secret({
            "id": "S002",
            "title": "secret",
            "status": "hidden",
            "description": "",
            "chapter_id": "002",
        })

        store.sync_state_update("002", {
            "characters": {"配角甲": {"name": "配角甲", "location": "训练室", "emotion": "紧张"}},
            "objects": [{"id": "O002", "name": "战术板", "holder": "配角甲", "status": "active"}],
            "threads": [{"id": "T002", "title": "晋级线", "status": "open", "summary": "支线"}],
        })

        _delete_chapter_dir(self.tmpdir, "002")

        with safe_connection(store.db_path) as conn:
            for table in [
                "events",
                "timeline_nodes",
                "timeline_edges",
                "foreshadows",
                "hooks",
                "reader_promises",
                "secrets",
                "state_change_candidates",
                "chapter_versions",
                "chapter_rewrites",
                "reader_feedback",
            ]:
                count = conn.execute(
                    f"select count(*) from {table} where chapter_id = ?",
                    ("002",),
                ).fetchone()[0]
                self.assertEqual(count, 0, table)
            self.assertEqual(
                conn.execute("select count(*) from objects where id = 'O002'").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("select count(*) from threads where id = 'T002'").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("select count(*) from character_state where id = '配角甲'").fetchone()[0],
                0,
            )

    def test_list_chapters_counts_final_text_when_wordcount_report_missing(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "chapter_final.txt").write_text("林越进入战场。", encoding="utf-8")

            chapters = web_server.list_chapters(sync=True).items

            self.assertEqual(chapters[0].word_count, 6)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_generate_chapter_plan_uses_outline_and_ai_output(self):
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
            (outline_dir / "outline.json").write_text(
                json.dumps({
                    "title_options": ["旧书名"],
                    "core_theme": "电竞逆袭",
                    "protagonist": {"name": "沈星璃"},
                    "macro_outline": [{"arc_id": "A01", "name": "起势", "chapters": "1-20", "goal": "打进职业圈"}],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            response = {
                "arc_id": "A01",
                "arc_name": "起势",
                "arc_goal": "打进职业圈",
                "chapters": [
                    {"chapter_id": "001", "chapter_title": "开播", "chapter_goal": "沈星璃用直播证明自己"},
                    {"chapter_id": "002", "chapter_title": "约战", "chapter_goal": "沈星璃接到强敌挑战"},
                ],
            }
            with patch("novel_agent.agents.base.StaticLLM.generate", return_value=json.dumps(response, ensure_ascii=False)):
                result = web_server.generate_chapter_plan(ChapterPlanRequest(start_chapter=1, count=2))

            self.assertEqual(len(result["chapters"]), 2)
            self.assertEqual(result["chapters"][0]["goal"], "沈星璃用直播证明自己")
            self.assertIn("沈星璃", result["outline"]["protagonist"]["name"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_get_chapter_marks_empty_final_text_as_empty_status(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_008"
            (chapter_dir / "reports").mkdir(parents=True)
            (chapter_dir / "plan.json").write_text(
                json.dumps({"chapter_title": "Empty", "target_chars": [1200, 2200]}),
                encoding="utf-8",
            )
            (chapter_dir / "chapter_final.txt").write_text("", encoding="utf-8")

            detail = web_server.get_chapter("008")

            self.assertEqual(detail.wordcount["count"], 0)
            self.assertEqual(detail.wordcount["status"], "empty")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_resume_audit_keeps_checkpoint_and_submits_goal(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR

        class DummyTaskManager:
            def __init__(self):
                self.submitted = None

            async def submit_chapter(self, chapter_id, goal, dry_run=False):
                self.submitted = {"chapter_id": chapter_id, "goal": goal, "dry_run": dry_run}
                return "task-resume"

            def get_task(self, task_id):
                return {"task_id": task_id, "status": "pending", "chapter_id": "003"}

            async def get_task_async(self, task_id):
                return self.get_task(task_id)

        dummy = DummyTaskManager()
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
                    }
                ),
                encoding="utf-8",
            )
            (chapter_dir / "plan.json").write_text(
                json.dumps({"chapter_goal": "继续审校"}),
                encoding="utf-8",
            )

            import asyncio
            from web.routes.chapters import tasks as chapter_tasks

            with patch.object(web_server, "_get_task_manager", return_value=dummy):
                result = asyncio.run(chapter_tasks.resume_chapter_audit("003"))

            self.assertTrue((chapter_dir / "checkpoint.json").exists())
            self.assertEqual(result.task_id, "task-resume")
            self.assertEqual(dummy.submitted["goal"], "继续审校")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_rewrite_chapter_submits_existing_chapter_goal(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR

        class DummyTaskManager:
            def __init__(self):
                self.submitted = None

            async def submit_chapter(self, chapter_id, goal, dry_run=False):
                self.submitted = {"chapter_id": chapter_id, "goal": goal, "dry_run": dry_run}
                return "task-1"

            def get_task(self, task_id):
                return {"task_id": task_id, "status": "pending", "chapter_id": "008"}

            async def get_task_async(self, task_id):
                return self.get_task(task_id)

        dummy = DummyTaskManager()
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_008"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "plan.json").write_text(
                json.dumps({"chapter_title": "Old", "chapter_goal": "Rewrite this beat"}),
                encoding="utf-8",
            )

            import asyncio
            with patch.object(web_server, "_get_task_manager", return_value=dummy):
                result = asyncio.run(web_server.rewrite_chapter("008"))

            self.assertEqual(result.task_id, "task-1")
            self.assertEqual(dummy.submitted["chapter_id"], "008")
            self.assertEqual(dummy.submitted["goal"], "Rewrite this beat")
            self.assertFalse(dummy.submitted["dry_run"])
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_list_chapters_detects_gaps_and_creates_missing_placeholders(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            # Create chapter_001 and chapter_004 to create gaps on 002 and 003
            c1_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
            c4_dir = self.tmpdir / "workspace" / "chapters" / "chapter_004"
            c1_dir.mkdir(parents=True)
            c4_dir.mkdir(parents=True)
            
            (c1_dir / "chapter_final.txt").write_text("第一章正文", encoding="utf-8")
            (c4_dir / "chapter_final.txt").write_text("第四章正文", encoding="utf-8")
            (c1_dir / "plan.json").write_text(json.dumps({"chapter_title": "起"}), encoding="utf-8")
            (c4_dir / "plan.json").write_text(json.dumps({"chapter_title": "合"}), encoding="utf-8")
            
            chapters = web_server.list_chapters(sync=True, include_gaps=True).items
            
            # Should return 4 chapters: 001, 002, 003, 004
            self.assertEqual(len(chapters), 4)
            self.assertEqual(chapters[0].chapter_id, "001")
            self.assertFalse(chapters[0].is_missing)
            
            self.assertEqual(chapters[1].chapter_id, "002")
            self.assertTrue(chapters[1].is_missing)
            self.assertEqual(chapters[1].title, "[缺失断档章]")
            
            self.assertEqual(chapters[2].chapter_id, "003")
            self.assertTrue(chapters[2].is_missing)
            
            self.assertEqual(chapters[3].chapter_id, "004")
            self.assertFalse(chapters[3].is_missing)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_suggest_chapter_goal_endpoint(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            # Case 1: Outline exists with chapter preset
            ws_dir = self.tmpdir / "workspace"
            ws_dir.mkdir(parents=True, exist_ok=True)
            outline_data = {
                "title_options": ["测试小说"],
                "core_theme": "主题",
                "logline": "梗概",
                "conflict": "冲突",
                "protagonist": {"name": "林越"},
                "chapters": [
                    {"chapter_id": "002", "goal": "这是大纲预设的第二章目标"}
                ]
            }
            (ws_dir / "outline.json").write_text(json.dumps(outline_data, ensure_ascii=False), encoding="utf-8")
            
            client = TestClient(web_app)
            response = client.get("/api/chapters/002/suggest-goal")
            self.assertEqual(response.status_code, 200)
            res_json = response.json()
            self.assertEqual(res_json["goal"], "这是大纲预设的第二章目标")
            self.assertEqual(res_json["source"], "outline_preset")

            # Case 2: No chapter preset, triggers AI generation
            # Fake the PipelineConfig while preserving the real LLM generate(role, prompt) contract.
            with patch("novel_agent.pipeline.PipelineConfig.from_config") as mock_from_config:
                class FakeLLM:
                    def generate(self, role, prompt):
                        self.role = role
                        self.prompt = prompt
                        return "AI预测出来的第三章目标"

                fake_llm = FakeLLM()
                mock_config = MagicMock()
                mock_config.get_llm.return_value = fake_llm
                mock_from_config.return_value = mock_config

                response = client.get("/api/chapters/003/suggest-goal")
                self.assertEqual(response.status_code, 200)
                res_json = response.json()
                self.assertEqual(res_json["goal"], "AI预测出来的第三章目标")
                self.assertEqual(res_json["source"], "ai_predicted")
                self.assertEqual(fake_llm.role, "managing_editor")
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_save_chapter(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            # Setup dummy chapter directory
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
            chapter_dir.mkdir(parents=True, exist_ok=True)
            
            plan_data = {
                "chapter_title": "原本的标题",
                "chapter_goal": "原本的目标",
                "target_chars": [1000, 2000]
            }
            (chapter_dir / "plan.json").write_text(json.dumps(plan_data, ensure_ascii=False), encoding="utf-8")
            (chapter_dir / "chapter_final.txt").write_text("原本的章节正文内容。", encoding="utf-8")
            
            client = TestClient(web_app)
            response = client.put(
                "/api/chapters/001",
                json={"title": "修改后的全新标题", "final_text": "这是手动编辑保存后的全新章节正文。"}
            )
            self.assertEqual(response.status_code, 200)
            res_json = response.json()
            self.assertEqual(res_json["status"], "saved")
            self.assertEqual(res_json["chapter_id"], "001")
            
            # Verify changes written to disk
            updated_plan = json.loads((chapter_dir / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(updated_plan["chapter_title"], "修改后的全新标题")
            
            updated_text = (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8")
            self.assertEqual(updated_text, "这是手动编辑保存后的全新章节正文。")
            authoritative = SQLiteStateStore(self.tmpdir).get_manuscript_document("001")
            self.assertEqual(authoritative["plain_text"], updated_text)
            self.assertEqual(authoritative["title"], "修改后的全新标题")
            self.assertEqual(authoritative["revision"], res_json["revision"])
            
            # Verify wordcount was recalculated
            wordcount_report_data = json.loads((chapter_dir / "reports" / "wordcount.json").read_text(encoding="utf-8"))
            self.assertGreater(wordcount_report_data["count"], 0)
            
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_create_new_chapter(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            (self.tmpdir / "workspace").mkdir(parents=True, exist_ok=True)

            client = TestClient(web_app)
            response = client.post(
                "/api/chapters",
                json={"chapter_id": "009", "title": "自定义全新测试章节"}
            )
            self.assertEqual(response.status_code, 200)
            res_json = response.json()
            self.assertEqual(res_json["status"], "created")
            self.assertEqual(res_json["chapter_id"], "009")
            
            # Check files created
            chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_009"
            self.assertTrue(chapter_dir.exists())
            
            plan = json.loads((chapter_dir / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["chapter_title"], "自定义全新测试章节")
            self.assertEqual(plan["chapter_id"], "009")
            
            final_txt = (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8")
            self.assertEqual(final_txt, "")
            
            wordcount = json.loads((chapter_dir / "reports" / "wordcount.json").read_text(encoding="utf-8"))
            self.assertEqual(wordcount["count"], 0)
            
            # Test duplicate returns error
            dup_resp = client.post(
                "/api/chapters",
                json={"chapter_id": "009", "title": "重复章节"}
            )
            self.assertEqual(dup_resp.status_code, 400)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base

    def test_delete_custom_asset(self):
        original_active = web_server._active_project_id
        original_base = web_server.BASE_DIR
        try:
            web_server.BASE_DIR = self.tmpdir
            web_server._active_project_id = None
            
            client = TestClient(web_app)
            
            # 1. 创建自定义资产
            create_payload = {
                "name": "my_custom_asset",
                "label": "我的自定义素材",
                "extension": "md",
                "content": "一些测试内容"
            }
            res = client.post("/api/assets", json=create_payload)
            self.assertEqual(res.status_code, 200)
            
            # 验证文件存在
            asset_file = self.tmpdir / "assets" / "custom" / "my_custom_asset.md"
            self.assertTrue(asset_file.exists())
            
            # 2. 删除自定义资产
            del_res = client.delete("/api/assets/my_custom_asset")
            self.assertEqual(del_res.status_code, 200)
            self.assertFalse(asset_file.exists())
            
            # 3. 尝试删除内置资产（应报错 400）
            del_builtin = client.delete("/api/assets/world_bible")
            self.assertEqual(del_builtin.status_code, 400)
        finally:
            web_server._active_project_id = original_active
            web_server.BASE_DIR = original_base
