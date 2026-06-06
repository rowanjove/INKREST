"""Report staleness on goal change."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.services.report_validity import (
    invalidate_chapter_reports,
    load_report_validity,
)


class ReportValidityTests(unittest.TestCase):
    def test_invalidate_marks_reports(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-stale-"))
        reports = tmp / "reports"
        reports.mkdir(parents=True)
        (reports / "audit.json").write_text('{"risk_level": "低"}', encoding="utf-8")
        manifest = invalidate_chapter_reports(reports, reason="goal_hash_mismatch", goal_hash="abc")
        self.assertFalse(manifest.get("valid", True) is not False)
        audit = json.loads((reports / "audit.json").read_text(encoding="utf-8"))
        self.assertTrue(audit.get("stale"))
        loaded = load_report_validity(reports)
        self.assertEqual(loaded.get("reason"), "goal_hash_mismatch")