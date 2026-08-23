"""Per-scene expression contract tests."""

import tempfile
import unittest
from pathlib import Path

from novel_agent.quality.character_voice import build_character_voice_profile, save_character_voice_profiles
from novel_agent.quality.scene_expression import (
    build_scene_expression_contract,
    normalise_scene_expression_contract,
)


class TestSceneExpressionContract(unittest.TestCase):
    def test_normalises_planner_aliases_without_inventing_values(self):
        payload = normalise_scene_expression_contract(
            {
                "scene_id": "002-01",
                "point_of_view": "林澈",
                "distance": "near",
                "tension_curve": "从试探升到逼问",
                "dialogue_intent": [{"character": "林澈", "intent": "套话", "subtext": "不暴露秘密"}],
                "motifs": ["雨声"],
            },
            chapter_id="002",
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["pov"], "林澈")
        self.assertEqual(payload["narrative_distance"], "near")
        self.assertEqual(payload["pressure_curve"], "从试探升到逼问")
        self.assertIn("林澈；套话；潜台词：不暴露秘密", payload["dialogue_intents"])
        self.assertEqual(payload["allowed_motifs"], ["雨声"])
        self.assertEqual(payload["policy"]["blocking"], False)

    def test_contract_combines_scene_controls_voice_and_expression_memory(self):
        with tempfile.TemporaryDirectory(prefix="scene-expression-contract-") as raw_root:
            root = Path(raw_root)
            chapter = root / "workspace" / "chapters" / "chapter_001"
            chapter.mkdir(parents=True)
            (chapter / "chapter_final.txt").write_text("她的手指轻轻敲着桌面。", encoding="utf-8")
            profile = build_character_voice_profile("linche", ["别解释。现在走。"], name="林澈")
            save_character_voice_profiles(root, {"linche": profile})

            contract = build_scene_expression_contract(
                root,
                "002",
                {
                    "scene_id": "002-01",
                    "pov": "林澈",
                    "characters": ["linche"],
                    "narrative_distance": "near",
                    "pressure_curve": "上升",
                    "dialogue_intents": ["试探"],
                    "allowed_motifs": ["雨声"],
                },
            )

            self.assertIn("[SCENE_EXPRESSION_CONTRACT v1]", contract)
            self.assertIn("POV：林澈", contract)
            self.assertIn("角色声口参考", contract)
            self.assertIn("林澈", contract)
            self.assertIn("[EXPRESSION_CONTRACT]", contract)
            self.assertIn("合同策略", contract)
            self.assertLessEqual(len(contract), 2400)


if __name__ == "__main__":
    unittest.main()
