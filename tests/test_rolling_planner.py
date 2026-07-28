"""Tests for rolling chapter queue planner."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from novel_agent.control.outline_structure import normalize_macro_outline
from novel_agent.services.rolling_planner import (
    append_briefs_to_queue,
    count_pending_briefs,
    format_chapter_id,
    max_generated_chapter_num,
)


class RollingPlannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="novel-roll-"))
        (self.tmp / "workspace").mkdir(parents=True)
        outline = {
            "target_chapters": 2000,
            "scale_profile": {"scale": "epic", "planning_window": 20, "max_chapters": 3000},
            "macro_outline": normalize_macro_outline(
                [{"arc_id": "A01", "chapters": "1-2000", "goal": "主线"}],
                target_chapters=2000,
                scale="epic",
            ),
        }
        (self.tmp / "workspace" / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )

    def test_format_chapter_id(self):
        self.assertEqual(format_chapter_id(1), "001")
        self.assertEqual(format_chapter_id(1000), "1000")

    def test_append_and_count_pending(self):
        arc = {
            "arc_id": "A01_01",
            "chapters": [
                {"chapter_id": "001", "chapter_goal": "a"},
                {"chapter_id": "002", "chapter_goal": "b"},
            ],
        }
        append_briefs_to_queue(self.tmp, arc)
        self.assertTrue((self.tmp / "workspace" / "arc_A01_01.json").exists())

        def never_done(_cid: str) -> bool:
            return False

        self.assertEqual(count_pending_briefs(self.tmp, never_done), 2)

    def test_max_generated_from_disk(self):
        d = self.tmp / "workspace" / "chapters" / "chapter_005"
        d.mkdir(parents=True)
        (d / "chapter_final.txt").write_text("x" * 200, encoding="utf-8")
        self.assertGreaterEqual(max_generated_chapter_num(self.tmp), 5)


class ChiefEditorNormalizeTests(unittest.TestCase):
    def test_chief_editor_applies_normalize(self):
        from novel_agent.agents.chief_editor import ChiefEditorAgent

        agent = ChiefEditorAgent(llm=MagicMock(), prompts=None)
        outline = {
            "protagonist": {"name": "a"},
            "scale_profile": {"scale": "epic"},
            "macro_outline": [{"arc_id": "A01", "chapters": "1-500", "goal": "g"}],
        }
        out = agent._validate_outline(outline, "t", "玄幻", 2000)
        self.assertGreater(len(out["macro_outline"]), 5)


if __name__ == "__main__":
    unittest.main()