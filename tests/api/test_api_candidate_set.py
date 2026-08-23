from tests.api._base import *  # noqa: F403


class ApiCandidateSetTests(ApiTestBase):
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
            json.dumps({"chapter_id": "001", "chapter_title": "第一章"}, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_explicit_candidate_set_review_and_feedback(self):
        client = TestClient(web_app)
        workspace = client.get("/api/manuscript/workspace", params={"chapter_id": "001"}).json()
        self.assertEqual(workspace["document"]["revision"], 1)

        created = client.post(
            "/api/manuscript/documents/001/candidate-set",
            json={
                "expected_revision": 1,
                "content_lock": {"contract_id": "lock-1"},
                "candidates": [
                    {"candidate_id": "a", "text": "新稿甲。"},
                    {"candidate_id": "b", "text": "新稿乙。"},
                ],
            },
        )
        self.assertEqual(created.status_code, 200)
        self.assertFalse(created.json()["enabled"])
        self.assertEqual(len(created.json()["candidates"]), 2)

        reviewed = client.get("/api/manuscript/documents/001/candidate-set")
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.json()["ranked_candidates"][0]["feedback_score"], 0)

        feedback = client.post(
            "/api/manuscript/documents/001/candidate-set/feedback",
            json={
                "feedback": {
                    "kind": "pairwise",
                    "candidate_a": "a",
                    "candidate_b": "b",
                    "choice": "a",
                }
            },
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(feedback.json()["status"], "recorded")
        self.assertEqual(feedback.json()["ranked_candidates"][0]["candidate_id"], "a")

        timeline = client.get("/api/manuscript/documents/001/candidate-set/timeline")
        self.assertEqual(timeline.status_code, 200)
        created_snapshot = next(item for item in timeline.json()["timeline"] if item["event"] == "created")
        old_set_id = timeline.json()["candidate_set_id"]
        rolled_back = client.post(
            "/api/manuscript/documents/001/candidate-set/rollback",
            json={
                "timeline_id": created_snapshot["timeline_id"],
                "expected_candidate_set_id": old_set_id,
            },
        )
        self.assertEqual(rolled_back.status_code, 200)
        self.assertNotEqual(rolled_back.json()["candidate_set"]["candidate_set_id"], old_set_id)
        self.assertEqual(rolled_back.json()["ranked_candidates"][0]["feedback_score"], 0)
        self.assertEqual(
            (self.tmpdir / "workspace" / "chapters" / "chapter_001" / "chapter_final.txt").read_text(
                encoding="utf-8"
            ),
            "旧正文。",
        )

    def test_candidate_set_requires_current_revision(self):
        client = TestClient(web_app)
        client.get("/api/manuscript/workspace", params={"chapter_id": "001"})
        response = client.post(
            "/api/manuscript/documents/001/candidate-set",
            json={"expected_revision": 2, "candidates": [{"text": "候选。"}]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "DOCUMENT_CONFLICT")

    def test_explicit_candidate_adoption_creates_revision(self):
        client = TestClient(web_app)
        client.get("/api/manuscript/workspace", params={"chapter_id": "001"})
        created = client.post(
            "/api/manuscript/documents/001/candidate-set",
            json={
                "expected_revision": 1,
                "candidates": [{"candidate_id": "a", "text": "新正文。"}],
            },
        )
        self.assertEqual(created.status_code, 200)
        set_id = created.json()["candidate_set_id"]
        adopted = client.post(
            "/api/manuscript/documents/001/candidate-set/candidates/a/adopt",
            json={"expected_revision": 1, "expected_candidate_set_id": set_id},
        )
        self.assertEqual(adopted.status_code, 200)
        self.assertEqual(adopted.json()["status"], "accepted")
        self.assertEqual(adopted.json()["document"]["revision"], 2)
        self.assertEqual(adopted.json()["event"]["kind"], "accept")
        self.assertEqual(
            (self.tmpdir / "workspace" / "chapters" / "chapter_001" / "chapter_final.txt").read_text(
                encoding="utf-8"
            ),
            "新正文。",
        )
        stale = client.post(
            "/api/manuscript/documents/001/candidate-set/candidates/a/adopt",
            json={"expected_revision": 1, "expected_candidate_set_id": set_id},
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "DOCUMENT_CONFLICT")

    def test_pairwise_api_keeps_candidate_ids_server_side(self):
        client = TestClient(web_app)
        client.get("/api/manuscript/workspace", params={"chapter_id": "001"})
        created = client.post(
            "/api/manuscript/documents/001/candidate-set",
            json={
                "expected_revision": 1,
                "candidates": [
                    {"candidate_id": "a", "text": "候选甲。"},
                    {"candidate_id": "b", "text": "候选乙。"},
                ],
            },
        )
        set_id = created.json()["candidate_set_id"]
        session = client.post(
            "/api/manuscript/documents/001/candidate-set/pairwise",
            json={"expected_candidate_set_id": set_id, "candidate_a": "a", "candidate_b": "b"},
        )
        self.assertEqual(session.status_code, 200)
        self.assertNotIn("candidate_a_id", session.json())
        self.assertNotIn("candidate_b_id", session.json())
        self.assertEqual({item["label"] for item in session.json()["options"]}, {"A", "B"})

        submitted = client.post(
            f"/api/manuscript/documents/001/candidate-set/pairwise/{session.json()['session_id']}/feedback",
            json={"choice": "A".lower()},
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "recorded")
        self.assertNotIn("candidate_a", submitted.json())
        duplicate = client.post(
            f"/api/manuscript/documents/001/candidate-set/pairwise/{session.json()['session_id']}/feedback",
            json={"choice": "b"},
        )
        self.assertEqual(duplicate.status_code, 422)
