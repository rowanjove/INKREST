from tests.api._base import *  # noqa: F403


class ApiQualityCenterTests(ApiTestBase):
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
        (reports_dir / "quality.json").write_text(
            json.dumps(
                {
                    "overall_pass": True,
                    "overall_score": 90,
                    "checks": {"prose_identity": {"status": "uncalibrated", "deviations": {}}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        web_server._active_project_id = self.original_active
        web_server.BASE_DIR = self.original_base
        super().tearDown()

    def test_calibration_voice_lab_and_metrics_endpoints(self):
        client = TestClient(web_app)
        sample = "雨停在旧城区的屋檐上。林澈握紧铜钥匙，沿着石阶向下走去。"
        saved = client.post(
            "/api/quality/calibration/golden",
            json={"minimum_samples": 20, "chapters": [{"chapter_id": "001", "text": sample}]},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["calibration"]["status"], "uncalibrated")

        feedback = client.post(
            "/api/quality/calibration/feedback",
            json={"kind": "false_positive", "case_id": "001:style"},
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(feedback.json()["event"]["kind"], "false_positive")

        freeze = client.post("/api/quality/voice-lab/freeze", json={"frozen": True, "reason": "人工锁定"})
        self.assertEqual(freeze.status_code, 200)
        self.assertTrue(freeze.json()["voice_lab"]["frozen"])
        voice_feedback = client.post(
            "/api/quality/voice-lab/feedback",
            json={"kind": "false_positive", "chapter_id": "001"},
        )
        self.assertEqual(voice_feedback.status_code, 200)

        metrics = client.get("/api/quality/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(metrics.json()["status"], "uncalibrated")
        csv_response = client.get("/api/quality/metrics/export", params={"format": "csv"})
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("chapter_id", csv_response.text)

    def test_quality_review_returns_chapter_evidence(self):
        client = TestClient(web_app)
        review = client.get("/api/quality/review", params={"chapter_id": "001"})
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.json()["chapter_id"], "001")
        self.assertIn("l1", review.json()["levels"])
        self.assertEqual(review.json()["quality_decision"]["status"], "pass")
        self.assertIn("issues", review.json())

    def test_quality_review_keeps_detail_and_nested_gate_evidence(self):
        reports = (
            self.tmpdir
            / "workspace"
            / "chapters"
            / "chapter_001"
            / "reports"
        )
        (reports / "quality.json").write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "guard_summary": {
                        "overall_status": "FAIL",
                        "blocked_by": ["continuity_physical"],
                    },
                    "checks": {
                        "continuity_physical": {
                            "pass": False,
                            "details": ["缺少关键实体位置承接"],
                        }
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (reports / "unified_gate.json").write_text(
            json.dumps(
                {"quality": {"blocked_by": ["continuity_physical"]}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        review = TestClient(web_app).get(
            "/api/quality/review", params={"chapter_id": "001"}
        )

        self.assertEqual(review.status_code, 200)
        evidence = review.json()["evidence"]
        self.assertTrue(
            any(item["kind"] == "quality_detail" for item in evidence)
        )
        self.assertTrue(
            any(item["kind"] == "gate_failure" for item in evidence)
        )

    def test_quality_review_explains_high_score_advisory_without_blocking(self):
        report_path = (
            self.tmpdir
            / "workspace"
            / "chapters"
            / "chapter_001"
            / "reports"
            / "quality.json"
        )
        report_path.write_text(
            json.dumps(
                {
                    "overall_pass": False,
                    "overall_score": 90,
                    "guard_summary": {"overall_status": "WARN", "blocked_by": []},
                    "chapter_score": {"score": 9.1, "keep": True, "blocked_by": []},
                    "checks": {
                        "style": {
                            "pass": False,
                            "level": "fail",
                            "score": 85,
                            "details": ["连续三段句式过于相似"],
                            "findings": [{
                                "message": "第 4 段与第 5 段句式重复",
                                "suggestion": "合并其中一段并调整句式。",
                                "location": "chapter_final.txt",
                                "span": {"line_start": 12, "line_end": 18},
                            }],
                        }
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        review = TestClient(web_app).get("/api/quality/review", params={"chapter_id": "001"})
        self.assertEqual(review.status_code, 200)
        body = review.json()
        self.assertEqual(body["quality_decision"]["status"], "review")
        self.assertFalse(body["quality_decision"]["blocking"])
        self.assertEqual(body["quality_decision"]["title"], "可保留，建议优化")
        self.assertFalse(body["issues"][0]["blocking"])
        self.assertEqual(body["issues"][0]["span"]["line_start"], 12)
