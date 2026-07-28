from tests.api._base import *  # noqa: F403

from novel_agent.services.manuscript_documents import plain_text_to_tiptap


class ApiPublishingTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        self.store = SQLiteStateStore(self.tmpdir)
        meta = self.tmpdir / "config" / "project_meta.json"
        meta.parent.mkdir(parents=True)
        meta.write_text(
            json.dumps(
                {"name": "数据库之书", "platform": "fanqie"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._document(
            "001",
            "雨夜",
            "数据库中的第一章。",
            disk_text="不应出现在发布中心的旧文件。",
        )
        self._document("002", "来信", "数据库中的第二章。")

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def _document(
        self,
        chapter_id: str,
        title: str,
        text: str,
        *,
        disk_text: str = "",
    ) -> None:
        self.store.create_manuscript_document(
            chapter_id=chapter_id,
            title=title,
            content_json=plain_text_to_tiptap(text),
            plain_text=text,
            markdown_text=text,
            source="test",
        )
        self.store.index_chapter(
            chapter_id,
            title,
            self.tmpdir
            / "workspace"
            / "chapters"
            / f"chapter_{chapter_id}"
            / "chapter_final.txt",
            len(text),
            "",
            has_final=True,
            gate_status="passed",
        )
        if disk_text:
            chapter_dir = (
                self.tmpdir / "workspace" / "chapters" / f"chapter_{chapter_id}"
            )
            chapter_dir.mkdir(parents=True, exist_ok=True)
            (chapter_dir / "chapter_final.txt").write_text(
                disk_text,
                encoding="utf-8",
            )

    def test_workspace_uses_sqlite_and_returns_all_publication_checks(self):
        response = TestClient(web_app).get(
            "/api/publishing/workspace",
            params={"chapter_id": "002"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["book"]["title"], "数据库之书")
        self.assertEqual(payload["book"]["chapter_count"], 2)
        self.assertNotIn("plain_text", payload["chapters"][0])
        self.assertEqual(payload["selected_chapter_id"], "002")
        self.assertEqual(payload["selected_chapter"]["plain_text"], "数据库中的第二章。")
        self.assertNotIn(
            "不应出现在发布中心的旧文件。",
            json.dumps(payload, ensure_ascii=False),
        )
        self.assertEqual(payload["platform"]["id"], "fanqie")
        self.assertEqual(payload["golden_check"]["ready_count"], 2)
        self.assertTrue(payload["preflight"]["can_export"])
        self.assertEqual(
            [item["id"] for item in payload["formats"]],
            ["txt", "markdown", "docx", "epub", "pdf"],
        )

    def test_export_requires_warning_acknowledgement_then_downloads_sqlite_text(self):
        client = TestClient(web_app)
        request = {
            "format": "txt",
            "title": "导出书名",
            "chapter_ids": ["001"],
        }

        warning = client.post("/api/publishing/export", json=request)
        self.assertEqual(warning.status_code, 409)
        self.assertEqual(warning.json()["code"], "EXPORT_WARNINGS_NOT_ACKNOWLEDGED")

        request["acknowledge_warnings"] = True
        exported = client.post("/api/publishing/export", json=request)

        self.assertEqual(exported.status_code, 200)
        self.assertIn("数据库中的第一章。", exported.content.decode("utf-8"))
        self.assertNotIn("不应出现在发布中心的旧文件。", exported.content.decode("utf-8"))
        self.assertIn("attachment", exported.headers["content-disposition"])

    def test_platform_and_feedback_mutations_return_refreshed_workspace(self):
        client = TestClient(web_app)

        platform = client.put(
            "/api/publishing/platform",
            json={"platform": "jinjiang"},
        )
        self.assertEqual(platform.status_code, 200)
        self.assertEqual(platform.json()["platform"]["id"], "jinjiang")

        feedback = client.put(
            "/api/publishing/feedback",
            json={
                "chapter_id": "001",
                "bounce_rate": 0.2,
                "retention_rate": 0.8,
                "active_readers": 120,
            },
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(feedback.json()["feedback"][0]["chapter_id"], "001")
        self.assertEqual(feedback.json()["feedback"][0]["active_readers"], 120)

        invalid = client.put(
            "/api/publishing/platform",
            json={"platform": "unknown"},
        )
        self.assertEqual(invalid.status_code, 422)

    def test_quality_failure_blocks_export(self):
        report = (
            self.tmpdir
            / "workspace"
            / "chapters"
            / "chapter_001"
            / "reports"
            / "quality.json"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "guard_summary": {
                        "overall_status": "FAIL",
                        "blocked_by": ["quality_gate"],
                    },
                }
            ),
            encoding="utf-8",
        )

        response = TestClient(web_app).post(
            "/api/publishing/export",
            json={
                "format": "txt",
                "title": "blocked",
                "acknowledge_warnings": True,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "EXPORT_PREFLIGHT_BLOCKED")
