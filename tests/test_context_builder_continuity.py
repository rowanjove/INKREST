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

    @patch('pathlib.Path.exists')
    def test_continuity_new_perspective(self, mock_exists):
        # 1. 模拟 plan.json 文件不存在（触发人名 Fallback 匹配逻辑）
        # 2. 模拟前一章最终文本存在，且内容不包含当前角色
        mock_exists.side_effect = lambda: True # 认为所有文件都存在
        
        # 模拟上一章结尾文本里只出现了林啸
        prev_text = "林啸独自走在夜雨中，回到了自己的居所。"
        
        # 模拟当前场景是新一章第一个场景，人物是林枫和苏晴（与上一章结尾无交集）
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫", "苏晴"],
            "entry": "林枫和苏晴正在大堂商议事情。"
        }
        
        # 查询已知角色的 mock
        self.mock_store.list_characters.return_value = {
            "linfeng": {"name": "林枫"},
            "suqing": {"name": "苏晴"},
            "linxiao": {"name": "林啸"}
        }

        # 我们对文件的 read_text 进行 mock
        with patch('pathlib.Path.read_text', return_value=prev_text) as mock_read:
            res = self.builder._get_previous_chapter_tail(scene)
            
            # 应该检测出 new_perspective，返回视角转换的提示，不带前章内容
            self.assertIn("视角转换", res)
            self.assertNotIn("林啸独自走在夜雨中", res)

    @patch('pathlib.Path.exists')
    def test_continuity_temporal_gap(self, mock_exists):
        # 模拟角色有交集，但 entry 匹配到时间跳跃词（三天后）
        mock_exists.side_effect = lambda: True
        
        # 上一章结尾出现林枫
        prev_text = "林枫独自坐在屋顶看着明月。"
        
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫"],
            "entry": "三天后，大雨终于停了，林枫背起行囊准备出发。"
        }
        
        self.mock_store.list_characters.return_value = {
            "linfeng": {"name": "林枫"}
        }
        
        with patch.object(self.builder, '_get_previous_chapter_summary', return_value="林枫历经磨难，决定前往宗门。"):
            with patch('pathlib.Path.read_text', return_value=prev_text):
                res = self.builder._get_previous_chapter_tail(scene)
                
                # 应该触发 temporal_gap，包含前章摘要，而不包含前章结尾文本
                self.assertIn("时空跃迁衔接背景", res)
                self.assertIn("林枫历经磨难", res)
                self.assertNotIn("林枫独自坐在屋顶", res)

    @patch('pathlib.Path.exists')
    def test_continuity_continuous(self, mock_exists):
        # 模拟角色有交集，无时间跳跃词，强连贯
        mock_exists.side_effect = lambda: True
        
        prev_text = "林枫看着缓缓倒下的林啸，攥紧了手中的长剑。"
        
        scene = {
            "scene_id": "002-01",
            "characters": ["林枫"],
            "entry": "林枫正要俯身从林啸的身上摸索解药。"
        }
        
        self.mock_store.list_characters.return_value = {
            "linfeng": {"name": "林枫"}
        }
        
        with patch('pathlib.Path.read_text', return_value=prev_text):
            res = self.builder._get_previous_chapter_tail(scene)
            
            # 应该判定为 continuous，包含前章结尾正文
            self.assertIn("时序无缝衔接参考", res)
            self.assertIn("林枫看着缓缓倒下的林啸", res)

    @patch('pathlib.Path.exists')
    def test_non_first_scene_ignored(self, mock_exists):
        # 章节内部非首个场景（如 scene-02），应该直接忽略前章衔接
        mock_exists.return_value = True
        scene = {
            "scene_id": "002-02",
            "characters": ["林枫"],
            "entry": "林枫继续走着。"
        }
        res = self.builder._get_previous_chapter_tail(scene)
        self.assertEqual(res, "")

if __name__ == '__main__':
    unittest.main()
