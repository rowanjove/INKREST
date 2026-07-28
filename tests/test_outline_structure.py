"""Tests for long-form macro outline normalization."""

import unittest

from novel_agent.control.outline_structure import normalize_macro_outline, _parse_chapter_range


class OutlineStructureTests(unittest.TestCase):
    def test_parse_range(self):
        self.assertEqual(_parse_chapter_range("1-3000"), (1, 3000))
        self.assertEqual(_parse_chapter_range("50"), (50, 50))

    def test_split_epic_monster_arc(self):
        macro = [{
            "arc_id": "A01",
            "name": "全书",
            "chapters": "1-3000",
            "goal": "主线",
        }]
        out = normalize_macro_outline(macro, target_chapters=3000, scale="epic")
        self.assertGreater(len(out), 30)
        spans = [_parse_chapter_range(a["chapters"]) for a in out]
        for start, end in spans:
            self.assertLessEqual(end - start + 1, 80)
        self.assertEqual(spans[0][0], 1)
        self.assertEqual(spans[-1][1], 3000)

    def test_short_unchanged(self):
        macro = [
            {"arc_id": "A01", "chapters": "1-10", "goal": "a"},
            {"arc_id": "A02", "chapters": "11-20", "goal": "b"},
        ]
        out = normalize_macro_outline(macro, target_chapters=20, scale="short")
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()