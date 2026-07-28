import tempfile
import unittest
from pathlib import Path

import yaml

from novel_agent.control.long_run import should_merge_review_stages


class MergeReviewTests(unittest.TestCase):
    def test_merge_default_true(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-merge-"))
        (tmp / "config").mkdir(parents=True)
        (tmp / "config" / "pipeline.yaml").write_text("runtime: {}\n", encoding="utf-8")
        self.assertTrue(should_merge_review_stages(tmp))

    def test_merge_can_disable(self):
        tmp = Path(tempfile.mkdtemp(prefix="novel-merge2-"))
        (tmp / "config").mkdir(parents=True)
        (tmp / "config" / "pipeline.yaml").write_text(
            yaml.safe_dump({"runtime": {"merge_review_stages": False}}),
            encoding="utf-8",
        )
        self.assertFalse(should_merge_review_stages(tmp))