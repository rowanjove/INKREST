import tempfile
import unittest
import shutil
from pathlib import Path

from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.utils.diff import compute_text_diff


class TestVersionsAndScrapbook(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-versions-test-"))
        self.store = SQLiteStateStore(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_version_lifecycle(self):
        # 1. 插入版本 A 并设为 active
        v_id_a = self.store.save_chapter_version(
            chapter_id="001",
            version_name="版本 A",
            content="这是第001章版本A的文字内容。",
            plan="{}",
            is_active=True,
            note="正史初始版本"
        )
        self.assertTrue(v_id_a)
        
        # 验证 list
        versions = self.store.list_chapter_versions("001")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["id"], v_id_a)
        self.assertEqual(versions[0]["is_active"], 1)

        # 2. 插入版本 B，设为非 active
        v_id_b = self.store.save_chapter_version(
            chapter_id="001",
            version_name="版本 B",
            content="这是第001章版本B的分支剧情文字内容。",
            plan="{}",
            is_active=False,
            note="第二走向"
        )
        
        # 验证 list 里有两个，且 A 依然是活跃的，B 是非活跃的
        versions = self.store.list_chapter_versions("001")
        self.assertEqual(len(versions), 2)
        active_ver = [v for v in versions if v["is_active"] == 1]
        self.assertEqual(len(active_ver), 1)
        self.assertEqual(active_ver[0]["id"], v_id_a)

        # 3. 插入版本 C 并设为 active (触发级联活跃重置)
        v_id_c = self.store.save_chapter_version(
            chapter_id="001",
            version_name="版本 C",
            content="这是第001章版本C的战力突破写法。",
            plan="{}",
            is_active=True,
            note="第三走向"
        )
        
        # 验证此时活跃的是 C，A 和 B 都是非活跃的
        versions = self.store.list_chapter_versions("001")
        self.assertEqual(len(versions), 3)
        
        active_ver = [v for v in versions if v["is_active"] == 1]
        self.assertEqual(len(active_ver), 1)
        self.assertEqual(active_ver[0]["id"], v_id_c)
        
        inactive_vers = [v for v in versions if v["is_active"] == 0]
        self.assertEqual(len(inactive_vers), 2)
        inactive_ids = {v["id"] for v in inactive_vers}
        self.assertIn(v_id_a, inactive_ids)
        self.assertIn(v_id_b, inactive_ids)

        # 4. 验证 set_active_chapter_version (重新切换回版本 A)
        self.store.set_active_chapter_version("001", v_id_a)
        versions = self.store.list_chapter_versions("001")
        active_ver = [v for v in versions if v["is_active"] == 1]
        self.assertEqual(active_ver[0]["id"], v_id_a)

        # 5. 验证删除版本分支
        # 尝试删除活跃分支 A 会抛错
        with self.assertRaises(ValueError):
            self.store.delete_chapter_version(v_id_a)
            
        # 成功删除非活跃分支 B
        self.store.delete_chapter_version(v_id_b)
        versions = self.store.list_chapter_versions("001")
        self.assertEqual(len(versions), 2)
        self.assertNotIn(v_id_b, {v["id"] for v in versions})

    def test_set_active_version_rejects_version_from_another_chapter(self):
        version_id = self.store.save_chapter_version(
            chapter_id="002",
            version_name="chapter 2",
            content="chapter 2 content",
            plan="{}",
            is_active=True,
        )

        with self.assertRaises(ValueError):
            self.store.set_active_chapter_version("001", version_id)

        active_versions = [
            version["id"]
            for version in self.store.list_chapter_versions("002")
            if version["is_active"] == 1
        ]
        self.assertEqual(active_versions, [version_id])

    def test_scrapbook_search(self):
        # 插入若干废稿（非活动版本）
        # 废稿1
        self.store.save_chapter_version(
            chapter_id="001",
            version_name="版本 B",
            content="第一自然段：林澈决定去深山探险。\n\n第二自然段：林澈在林府里修养，觉得十分无聊。\n\n第三自然段：天空中闪过一道神秘紫雷。",
            plan="{}",
            is_active=False,
            note="废弃走向一"
        )
        # 废稿2 (活动版本，不应被 Scrapbook 搜出)
        self.store.save_chapter_version(
            chapter_id="001",
            version_name="版本 A",
            content="这是一段非常精彩的正史段落。林澈在林府修行。",
            plan="{}",
            is_active=True,
            note="正史"
        )
        # 废稿3 (另一章的废稿)
        self.store.save_chapter_version(
            chapter_id="002",
            version_name="分支一",
            content="另一章的废弃段落：林澈斩杀了那头野兽。",
            plan="{}",
            is_active=False,
            note="废弃走向二"
        )
        
        # 1. 全局搜索“林府”
        results = self.store.search_scrapbook(query="林府")
        # 应该搜到：废稿1的第二自然段。而正史版本2里虽然有“林府”，但因为 is_active=1 不应该被搜到！
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chapter_id"], "001")
        self.assertEqual(results[0]["version_name"], "版本 B")
        self.assertIn("林府", results[0]["text"])

        # 2. 全局搜索“林澈”
        results_all = self.store.search_scrapbook(query="林澈")
        # 应该包含废稿1的第一、二自然段，以及废稿3（Ch 002）。一共3段！
        self.assertEqual(len(results_all), 3)

        # 3. 带章节过滤搜索
        results_ch1 = self.store.search_scrapbook(query="林澈", chapter_id="001")
        self.assertEqual(len(results_ch1), 2)
        
        results_ch2 = self.store.search_scrapbook(query="林澈", chapter_id="002")
        self.assertEqual(len(results_ch2), 1)
        self.assertIn("野兽", results_ch2[0]["text"])

        # 4. 测试单换行符分割的兼容性
        self.store.save_chapter_version(
            chapter_id="003",
            version_name="分支一",
            content="单换行第一段：林澈在练剑。\n单换行第二段：林澈在喝茶。",
            plan="{}",
            is_active=False,
            note="单换行废弃"
        )
        results_ch3 = self.store.search_scrapbook(query="林澈", chapter_id="003")
        self.assertEqual(len(results_ch3), 2)
        self.assertEqual(results_ch3[0]["text"], "单换行第一段：林澈在练剑。")
        self.assertEqual(results_ch3[1]["text"], "单换行第二段：林澈在喝茶。")

    def test_diff_utility(self):
        text_a = "林澈推开木门，走了出去。"
        text_b = "林澈轻轻推开沉重的木门，走了出去。"
        
        chunks = compute_text_diff(text_a, text_b)
        
        # 验证返回了 flat chunks 结构
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIn(chunk["type"], {"equal", "insert", "delete"})
            self.assertTrue(chunk["text"])
            
        # 验证变动匹配
        inserts = [c["text"] for c in chunks if c["type"] == "insert"]
        self.assertIn("轻轻", inserts)
        self.assertIn("沉重的", inserts)


if __name__ == "__main__":
    unittest.main()
