import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from novel_agent.agents.context_builder import ContextBuilderAgent

class TestContextBuilderContinuity(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path("/mock/root")
        self.mock_vector_store = MagicMock()
        
        # Mock SQLiteStateStore
        self.mock_store = MagicMock()
        
        with patch('novel_agent.agents.context_builder.SQLiteStateStore') as mock_class:
            mock_class.return_value = self.mock_store
            self.builder = ContextBuilderAgent(self.root_dir, self.mock_vector_store)

    def test_continuity_new_perspective(self):
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫", "苏晴"],
            "entry": "林枫和苏晴正在大堂商议事情。"
        }
        with patch.object(self.builder, "_get_prev_chapter_characters", return_value=["林啸"]):
            with patch.object(self.builder, "_get_previous_chapter_summary", return_value=""):
                with patch(
                    "novel_agent.services.manuscript_workspace.read_chapter_plain_text",
                    return_value="",
                ):
                    res = self.builder._get_previous_chapter_tail(scene)

        self.assertIn("视角转换", res)
        self.assertNotIn("林啸独自走在夜雨中", res)

    def test_continuity_temporal_gap(self):
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫"],
            "entry": "三天后，大雨终于停了，林枫背起行囊准备出发。"
        }
        with patch.object(self.builder, "_get_prev_chapter_characters", return_value=["林枫"]):
            with patch.object(
                self.builder,
                "_get_previous_chapter_summary",
                return_value="林枫历经磨难，决定前往宗门。",
            ):
                with patch(
                    "novel_agent.services.manuscript_workspace.read_chapter_plain_text",
                    return_value="林枫独自坐在屋顶看着明月。",
                ):
                    res = self.builder._get_previous_chapter_tail(scene)

        self.assertIn("时空跃迁衔接背景", res)
        self.assertIn("林枫历经磨难", res)
        self.assertNotIn("林枫独自坐在屋顶", res)

    def test_continuity_continuous(self):
        prev_text = "林枫看着缓缓倒下的林啸，攥紧了手中的长剑。"
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫"],
            "entry": "林枫正要俯身从林啸的身上摸索解药。"
        }
        with patch.object(self.builder, "_get_prev_chapter_characters", return_value=["林枫"]):
            with patch.object(self.builder, "_get_previous_chapter_summary", return_value=""):
                with patch(
                    "novel_agent.services.manuscript_workspace.read_chapter_plain_text",
                    return_value=prev_text,
                ):
                    res = self.builder._get_previous_chapter_tail(scene)

        self.assertIn("时序无缝衔接参考", res)
        self.assertIn("林枫看着缓缓倒下的林啸", res)

    def test_non_first_scene_ignored(self):
        scene = {
            "scene_id": "002-02",
            "characters": ["林枫"],
            "entry": "林枫继续走着。"
        }
        res = self.builder._get_previous_chapter_tail(scene)
        self.assertEqual(res, "")

if __name__ == '__main__':
    unittest.main()
