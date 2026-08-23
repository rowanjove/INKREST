"""Phase 0 quality-safety and evidence regression tests."""

import unittest

from novel_agent.quality.audit_schema import build_audit_error
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.settings import quality_gate_blocks
from novel_agent.quality.style_rules import check_ai_style, check_anti_ai_flavor


class TestQualityEvidence(unittest.TestCase):
    def test_ai_style_returns_span_evidence_and_clusters(self):
        text = (
            "林澈不禁深吸一口气，心中暗道门后的答案终于出现了。"
            "空气仿佛凝固，他的嘴角微微上扬。"
        )

        result = check_ai_style(text)

        self.assertGreaterEqual(len(result["findings"]), 4)
        finding = result["findings"][0]
        self.assertIn("rule_id", finding)
        self.assertIn("text", finding)
        self.assertIsInstance(finding["start"], int)
        self.assertIsInstance(finding["end"], int)
        self.assertLess(finding["start"], finding["end"])
        self.assertGreaterEqual(len(result["clusters"]), 1)
        self.assertTrue(all("finding_ids" in cluster for cluster in result["clusters"]))

    def test_single_style_hit_is_evidence_without_cluster(self):
        result = check_ai_style("他不禁抬头。")

        self.assertEqual(result["total_hits"], 1)
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["hits"], ["不禁"])

    def test_anti_ai_flavor_returns_span_evidence(self):
        text = "她感到愤怒。空气中弥漫着紧张。"

        result = check_anti_ai_flavor(text)

        self.assertGreaterEqual(len(result["findings"]), 2)
        self.assertTrue(all(finding["start"] < finding["end"] for finding in result["findings"]))


class TestAuditSafety(unittest.TestCase):
    def test_audit_error_is_explicit_and_not_low_risk(self):
        result = build_audit_error(RuntimeError("provider unavailable"), stage="audit")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["risk_level"], "unknown")
        self.assertEqual(result["issues"][0]["type"], "audit_error")
        self.assertEqual(result["issues"][0]["severity"], "high")
        self.assertEqual(result["issues"][0]["audit_class"], "CRITICAL")
        self.assertEqual(result["state_update"], {})

    def test_incomplete_audit_is_visible_and_strict_gate_blocks(self):
        report = build_quality_report(
            "林澈推开门，雨水从袖口滴到地上。",
            audit={"status": "error", "risk_level": "unknown"},
            mode="block_on_fail",
        )

        self.assertFalse(report["overall_pass"])
        self.assertTrue(report["incomplete"])
        self.assertEqual(report["audit"]["status"], "error")
        self.assertTrue(quality_gate_blocks(report, "block_on_fail"))
        self.assertFalse(quality_gate_blocks(report, "report_only"))

    def test_unified_gate_identifies_incomplete_audit(self):
        from novel_agent.services.unified_gate import _audit_is_incomplete

        self.assertTrue(_audit_is_incomplete({"status": "error"}))
        self.assertTrue(_audit_is_incomplete({"status": "unknown"}))
        self.assertFalse(_audit_is_incomplete({"risk_level": "低"}))


if __name__ == "__main__":
    unittest.main()
