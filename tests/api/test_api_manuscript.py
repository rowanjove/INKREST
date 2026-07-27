from tests.api._base import *  # noqa: F403


def _document(text: str):
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


class ApiManuscriptTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("旧正文。", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps(
                {
                    "chapter_id": "001",
                    "chapter_title": "第一章 雨夜",
                    "chapter_goal": "让主角发现密信",
                    "target_chars": [2000, 3000],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_workspace_lazily_imports_legacy_text_into_authoritative_document(self):
        response = TestClient(web_app).get(
            "/api/manuscript/workspace", params={"chapter_id": "001"}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["selected_chapter_id"], "001")
        self.assertEqual(payload["document"]["plain_text"], "旧正文。")
        self.assertEqual(payload["document"]["revision"], 1)
        self.assertEqual(payload["context"]["chapter_goal"], "让主角发现密信")

        store = SQLiteStateStore(self.tmpdir)
        self.assertEqual(store.get_manuscript_document("001")["plain_text"], "旧正文。")

    def test_save_projects_text_and_rejects_stale_revision(self):
        client = TestClient(web_app)
        initial = client.get(
            "/api/manuscript/workspace", params={"chapter_id": "001"}
        ).json()["document"]

        saved = client.put(
            "/api/manuscript/documents/001",
            json={
                "title": "第一章 新雨",
                "content_json": _document("新正文。"),
                "expected_revision": initial["revision"],
                "source": "autosave",
            },
        )

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["revision"], 2)
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        self.assertEqual(
            (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8"),
            "新正文。",
        )
        plan = json.loads((chapter_dir / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["chapter_title"], "第一章 新雨")

        conflict = client.put(
            "/api/manuscript/documents/001",
            json={
                "title": "过期覆盖",
                "content_json": _document("不应写入"),
                "expected_revision": 1,
                "source": "autosave",
            },
        )

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "DOCUMENT_CONFLICT")
        self.assertEqual(conflict.json()["current"]["revision"], 2)
        self.assertEqual(
            (chapter_dir / "chapter_final.txt").read_text(encoding="utf-8"),
            "新正文。",
        )

    def test_history_restore_creates_a_new_revision(self):
        client = TestClient(web_app)
        initial = client.get(
            "/api/manuscript/workspace", params={"chapter_id": "001"}
        ).json()["document"]
        saved = client.put(
            "/api/manuscript/documents/001",
            json={
                "title": initial["title"],
                "content_json": _document("第二版。"),
                "expected_revision": initial["revision"],
                "source": "manual",
            },
        ).json()
        history = client.get("/api/manuscript/documents/001/revisions").json()
        first_revision = next(item for item in history if item["revision"] == 1)

        restored = client.post(
            f"/api/manuscript/documents/001/revisions/{first_revision['revision_id']}/restore",
            json={"expected_revision": saved["revision"]},
        )

        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["revision"], 3)
        self.assertEqual(restored.json()["plain_text"], "旧正文。")
