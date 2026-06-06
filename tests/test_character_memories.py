import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import MagicMock

from novel_agent.agents.state_extractor import StateExtractorAgent
from novel_agent.state.manager import StateManager
from novel_agent.agents.context_builder import ContextBuilderAgent


class CharacterMemoriesTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-char-mem-test-"))
        self.assets_dir = self.tmpdir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        
        self.cards_data = {
            "characters": [
                {
                    "id": "protagonist",
                    "name": "主角",
                    "personality_constraints": [
                        "遇到危险先观察",
                        "警惕心强"
                    ],
                    "speech_style": [
                        "短句为主",
                        "冷言冷语"
                    ]
                }
            ]
        }
        with open(self.assets_dir / "character_cards.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(self.cards_data, f, allow_unicode=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_state_extractor_extracts_memories(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = """
        {
          "events": [{"id": "E001", "summary": "主角找到了钥匙"}],
          "characters": {"主角": {"location": "密室", "emotion": "紧张"}},
          "character_memories": [
            {
              "character": "主角",
              "summary": "在暗格中意外寻得了一柄生锈的黄铜钥匙",
              "emotional_impact": "产生了一丝希望，但对前路愈发感到疑虑"
            }
          ]
        }
        """
        agent = StateExtractorAgent(mock_llm)
        result = agent.extract("正文...", "001")
        
        self.assertEqual(len(result["character_memories"]), 1)
        self.assertEqual(result["character_memories"][0]["character"], "主角")
        self.assertEqual(result["character_memories"][0]["summary"], "在暗格中意外寻得了一柄生锈的黄铜钥匙")
        self.assertEqual(result["character_memories"][0]["emotional_impact"], "产生了一丝希望，但对前路愈发感到疑虑")

    def test_state_manager_merges_and_persists_memories(self):
        manager = StateManager(self.tmpdir)
        
        update1 = {
            "character_memories": [
                {
                    "character": "主角",
                    "summary": "发现密道",
                    "emotional_impact": "略感振奋"
                },
                {
                    "character": "路人甲",
                    "summary": "被主角搭救",
                    "emotional_impact": "对主角心存感激"
                }
            ]
        }
        manager.apply_update("001", update1)
        
        memories_path = self.assets_dir / "character_memories.yaml"
        self.assertTrue(memories_path.exists())
        
        data = yaml.safe_load(memories_path.read_text(encoding="utf-8"))
        self.assertIn("主角", data["characters"])
        self.assertIn("路人甲", data["characters"])
        
        self.assertEqual(data["characters"]["主角"]["core_traits"], ["遇到危险先观察", "警惕心强"])
        self.assertEqual(data["characters"]["主角"]["speech_patterns"], ["短句为主", "冷言冷语"])
        self.assertEqual(len(data["characters"]["主角"]["memories"]), 1)
        self.assertEqual(data["characters"]["主角"]["memories"][0]["summary"], "发现密道")
        
        self.assertEqual(data["characters"]["路人甲"]["core_traits"], [])
        self.assertEqual(data["characters"]["路人甲"]["speech_patterns"], [])
        self.assertEqual(data["characters"]["路人甲"]["memories"][0]["summary"], "被主角搭救")
        
        update2 = {
            "character_memories": [
                {
                    "character": "主角",
                    "summary": "发现密道",
                    "emotional_impact": "略感振奋"
                },
                {
                    "character": "主角",
                    "summary": "遭遇陷阱",
                    "emotional_impact": "更警惕"
                }
            ]
        }
        manager.apply_update("002", update2)
        
        data2 = yaml.safe_load(memories_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data2["characters"]["主角"]["memories"]), 2)
        self.assertEqual(data2["characters"]["主角"]["memories"][1]["summary"], "遭遇陷阱")

    def test_context_builder_injects_memories(self):
        mem_data = {
            "characters": {
                "主角": {
                    "core_traits": ["冷静", "多疑"],
                    "speech_patterns": ["少言寡语"],
                    "memories": [
                        {"summary": "事件1", "emotional_impact": "影响1"},
                        {"summary": "事件2", "emotional_impact": "影响2"},
                        {"summary": "事件3", "emotional_impact": "影响3"},
                        {"summary": "事件4", "emotional_impact": "影响4"}
                    ]
                }
            }
        }
        with open(self.assets_dir / "character_memories.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(mem_data, f, allow_unicode=True)
            
        builder = ContextBuilderAgent(self.tmpdir)
        scene = {
            "scene_id": "003-01",
            "characters": ["主角", "未录入角色"],
            "purpose": "主角探索遗迹",
            "entry": "进入遗迹大门",
            "exit": "到达内殿",
            "target_chars": 1000
        }
        
        context = builder.build("通过第一层关卡", scene)
        
        self.assertIn("登场角色性格与近期记忆", context)
        self.assertIn("主角", context)
        self.assertIn("冷静", context)
        self.assertIn("多疑", context)
        self.assertIn("少言寡语", context)
        self.assertIn("事件2", context)
        self.assertIn("事件3", context)
        self.assertIn("事件4", context)
        self.assertNotIn("事件1", context)
        self.assertNotIn("未录入角色", context)


if __name__ == "__main__":
    unittest.main()
