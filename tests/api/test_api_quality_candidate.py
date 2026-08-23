from tests.api._base import *  # noqa: F403

from novel_agent.services.manuscript_workspace import text_sha256


class ApiQualityCandidateTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.original_active = web_server._active_project_id
        self.original_base = web_server.BASE_DIR
        web_server.BASE_DIR = self.tmpdir
        web_server._active_project_id = None
        chapter_dir = self.tmpdir / "workspace" / "chapters" / "chapter_001"
        reports_dir = chapter_dir / "reports"
        reports_dir.mkdir(parents=True)
        (chapter_dir / "chapter_final.txt").write_text("旧正文。", encoding="utf-8")
        (chapter_dir / "plan.json").write_text(
            json.dumps({"chapter_id": "001", "chapter_title": "第一章"}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.reports_dir = reports_dir

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def _write_candidate(self, text="新正文。", *, accepted=True, status="accepted"):
        (self.reports_dir / "quality_rewrite_candidate.txt").write_text(text, encoding="utf-8")
        (self.reports_dir / "quality_rewrite_candidate.json").write_text(
            json.dumps(
                {
                    "accepted": accepted,
                    "status": status,
                    "source_sha256": text_sha256("旧正文。"),
                    "candidate_sha256": text_sha256(text),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_candidate_diff_and_manual_accept_create_revision(self):
        self._write_candidate()
        client = TestClient(web_app)
        workspace = client.get("/api/manuscript/workspace", params={"chapter_id": "001"}).json()
        self.assertEqual(workspace["document"]["revision"], 1)

        candidate = client.get("/api/manuscript/documents/001/quality-candidate")
        self.assertEqual(candidate.status_code, 200)
        self.assertEqual(candidate.json()["diff"]["stats"]["changed_blocks"], 1)
        self.assertEqual(candidate.json()["current_revision"], 1)

        accepted = client.post(
            "/api/manuscript/documents/001/quality-candidate/accept",
            json={"expected_revision": 1},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], "accepted")
        self.assertEqual(accepted.json()["document"]["revision"], 2)
        self.assertTrue(accepted.json()["metadata"]["adopted"])
        self.assertEqual(
            (self.tmpdir / "workspace" / "chapters" / "chapter_001" / "chapter_final.txt").read_text(
                encoding="utf-8"
            ),
            "新正文。",
        )

    def test_rejected_candidate_cannot_be_manually_accepted(self):
        self._write_candidate("短稿。", accepted=False, status="rejected")
        response = TestClient(web_app).post(
            "/api/manuscript/documents/001/quality-candidate/accept",
            json={"expected_revision": 1},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "QUALITY_CANDIDATE_REJECTED")
