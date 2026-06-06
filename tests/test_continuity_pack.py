"""Cross-chapter continuity pack tests."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.services.continuity_pack import (
    build_planner_continuity_block,
    enrich_plan_characters,
    prev_chapter_cast,
)


class ContinuityPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="continuity-pack-"))
        (self.tmp / "assets").mkdir(parents=True)
        (self.tmp / "assets" / "character_cards.yaml").write_text(
            "characters:\n  - id: protagonist\n    name: 林夏\n",
            encoding="utf-8",
        )
        ch1 = self.tmp / "workspace" / "chapters" / "chapter_001"
        ch1.mkdir(parents=True)
        (ch1 / "plan.json").write_text(
            json.dumps(
                {
                    "scenes": [
                        {
                            "scene_id": "001-01",
                            "pov": "林夏",
                            "characters": ["林夏", "队友阿凯"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (ch1 / "chapter_final.txt").write_text(
            "林夏握紧鼠标，阿凯在语音里催她拆包。",
            encoding="utf-8",
        )

    def test_prev_chapter_cast_reads_plan(self):
        cast = prev_chapter_cast(self.tmp, "002")
        self.assertIn("林夏", cast)
        self.assertIn("队友阿凯", cast)

    def test_enrich_plan_injects_characters(self):
        plan = {
            "chapter_id": "002",
            "scenes": [{"scene_id": "002-01", "purpose": "延续训练"}],
        }
        enriched = enrich_plan_characters(plan, self.tmp, "002")
        chars = enriched["scenes"][0].get("characters") or []
        self.assertIn("林夏", chars)

    def test_planner_block_mentions_roster(self):
        block = build_planner_continuity_block(self.tmp, "002", "第二场排位赛")
        self.assertIn("林夏", block)
        self.assertIn("上一章", block)


if __name__ == "__main__":
    unittest.main()