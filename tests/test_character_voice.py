"""Character voice profile and context tests."""

import tempfile
import unittest
from pathlib import Path

from novel_agent.quality.character_voice import (
    build_character_voice_context,
    build_character_voice_profile,
    compare_character_voice,
    extract_dialogue_samples,
    load_character_voice_profiles,
    save_character_voice_profiles,
)


class TestCharacterVoice(unittest.TestCase):
    def test_profile_keeps_sources_and_aggregate_voice_signals_only(self):
        profile = build_character_voice_profile(
            "linche",
            [
                {"id": "dialogue-1", "kind": "user_sample", "text": "别解释。现在走。"},
                {"id": "dialogue-2", "kind": "accepted_dialogue", "text": "你确定吗？我不信。"},
            ],
            name="林澈",
        )

        self.assertEqual(profile["character_id"], "linche")
        self.assertEqual(profile["name"], "林澈")
        self.assertEqual(profile["sample_count"], 2)
        self.assertEqual(len(profile["sources"]), 2)
        self.assertNotIn("别解释", profile["sources"][0])
        self.assertIn("utterance_length", profile["rhythm"])
        self.assertGreater(profile["speech_markers"]["question_rate"], 0)
        self.assertTrue(profile["profile_id"])

    def test_save_load_compare_and_context(self):
        with tempfile.TemporaryDirectory(prefix="character-voice-") as raw_root:
            root = Path(raw_root)
            profile = build_character_voice_profile(
                "linche",
                ["别解释。现在走。", "你确定吗？"],
                name="林澈",
                human_overrides={"speech_style": ["短句", "少解释"], "must_not": ["长篇演讲"]},
            )
            path = save_character_voice_profiles(root, {"linche": profile})
            loaded = load_character_voice_profiles(root)
            context = build_character_voice_context(root, ["linche"])
            comparison = compare_character_voice("别说了。走。", loaded["linche"])

            self.assertTrue(path.is_file())
            self.assertEqual(loaded["linche"]["profile_id"], profile["profile_id"])
            self.assertIn("林澈", context)
            self.assertIn("短句", context)
            self.assertIn("长篇演讲", context)
            self.assertTrue(comparison["pass"])
            self.assertFalse(comparison["blocking"])

    def test_extract_dialogue_samples_requires_explicit_speaker_pattern(self):
        text = "林澈说：“别解释。”沈砚道：“我只问一次。”旁白没有台词。"
        samples = extract_dialogue_samples(text, ["林澈", "沈砚"])

        self.assertEqual(samples["林澈"], ["别解释。"])
        self.assertEqual(samples["沈砚"], ["我只问一次。"])

    def test_context_builder_injects_voice_profile_only_when_present(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        with tempfile.TemporaryDirectory(prefix="character-voice-context-") as raw_root:
            root = Path(raw_root)
            profile = build_character_voice_profile("linche", ["别解释。现在走。"], name="林澈")
            save_character_voice_profiles(root, {"linche": profile})
            builder = ContextBuilderAgent(root)

            block = builder._build_character_voice_block({"characters": ["linche"]})

            self.assertIn("林澈", block)
            self.assertIn("句长中位数", block)


if __name__ == "__main__":
    unittest.main()
