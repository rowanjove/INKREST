# -*- coding: utf-8 -*-
import tempfile
import unittest
import shutil
import json
from pathlib import Path

from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.control.platform_profiles import resolve_platform_profile, PLATFORM_PROFILES
from novel_agent.agents.chapter_planner import ChapterPlannerAgent
from novel_agent.agents.writer import WriterAgent


class TestPlatformAndFeedback(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-p4-test-"))
        self.store = SQLiteStateStore(self.tmpdir)
        
        # 创建模拟项目目录及 meta 配置文件
        self.config_dir = self.tmpdir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.config_dir / "project_meta.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_platform_profiles_resolution(self):
        # 1. 验证获取有效的预设
        for key in ["qidian", "fanqie", "feilu", "jinjiang"]:
            profile = resolve_platform_profile(key)
            self.assertEqual(profile["name"], key)
            self.assertTrue(profile["label"])
            self.assertTrue(profile["style_prompt"])
            self.assertTrue(profile["golden_three_rules"])
            self.assertGreater(len(profile["rules_blacklist"]), 0)

        # 2. 验证无效的预设会自动降级为起点 (qidian)
        profile_invalid = resolve_platform_profile("non_existent_platform")
        self.assertEqual(profile_invalid["name"], "qidian")

    def test_reader_feedback_db_crud(self):
        # 1. 连续保存反馈数据
        fid_1 = self.store.save_reader_feedback(
            chapter_id="001",
            bounce_rate=0.12,
            retention_rate=0.85,
            active_readers=5000
        )
        self.assertTrue(fid_1)

        fid_2 = self.store.save_reader_feedback(
            chapter_id="002",
            bounce_rate=0.28,
            retention_rate=0.72,
            active_readers=4500
        )
        self.assertTrue(fid_2)

        # 2. 更新已有反馈
        fid_1_new = self.store.save_reader_feedback(
            chapter_id="001",
            bounce_rate=0.15,
            retention_rate=0.82,
            active_readers=5200
        )
        self.assertEqual(fid_1, fid_1_new)

        # 3. 单个查询
        fb = self.store.get_reader_feedback("001")
        self.assertIsNotNone(fb)
        self.assertEqual(fb["bounce_rate"], 0.15)
        self.assertEqual(fb["active_readers"], 5200)

        # 4. 批量最近查询，验证排序与翻转（按 chapter_id 升序排列）
        recent = self.store.get_recent_feedback(limit=5)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["chapter_id"], "001")
        self.assertEqual(recent[1]["chapter_id"], "002")

    def test_chapter_planner_golden_three_and_platform_prompt(self):
        # 1. 写入绑定的平台 meta 信息（设为番茄）
        meta_data = {"platform": "fanqie"}
        self.meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

        # 2. 实例化 ChapterPlannerAgent 并挂载属性
        # 这里用 None 作为 LLM，因为我们仅测试 _build_prompt 的字符拼接，不运行 run()
        agent = ChapterPlannerAgent(llm=None)
        agent.project_dir = self.tmpdir
        agent.store = self.store

        # 3. 测试第 1 章 (属于黄金三章范围)
        brief_ch1 = {
            "chapter_id": "001",
            "chapter_title": "初醒",
            "chapter_goal": "主角绑定神级选择系统"
        }
        prompt = agent._build_prompt(brief_ch1)
        
        # 验证是否包含番茄平台的 label 和避坑提示
        self.assertIn("番茄小说", prompt)
        # 验证包含黄金三章引导
        self.assertIn("黄金三章专项质量规则 (本章为第 1 章)", prompt)
        self.assertIn("第一章必须在 500 字内交代主角困境", prompt)

        # 4. 测试第 4 章 (不属于黄金三章范围)
        brief_ch4 = {
            "chapter_id": "004",
            "chapter_title": "出山",
            "chapter_goal": "主角第一次出门打怪"
        }
        prompt_ch4 = agent._build_prompt(brief_ch4)
        self.assertIn("番茄小说", prompt_ch4)
        self.assertNotIn("黄金三章专项质量规则", prompt_ch4)

    def test_adaptive_pacing_compensation(self):
        # 1. 写入绑定的平台 meta 信息（起点）
        meta_data = {"platform": "qidian"}
        self.meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

        agent = ChapterPlannerAgent(llm=None)
        agent.project_dir = self.tmpdir
        agent.store = self.store

        brief = {
            "chapter_id": "005",
            "chapter_title": "日常修炼",
            "chapter_goal": "主角在家修炼一整天"
        }

        # 场景一：低跳出率（无需危机补偿）
        self.store.save_reader_feedback("002", 0.12, 0.88, 5000)
        self.store.save_reader_feedback("003", 0.10, 0.90, 5100)
        self.store.save_reader_feedback("004", 0.14, 0.86, 4900)

        prompt_healthy = agent._build_prompt(brief)
        self.assertNotIn("读者流失危机节奏补偿指令", prompt_healthy)

        # 场景二：重度流失危机（跳出率爆发 40%）
        self.store.save_reader_feedback("002", 0.38, 0.60, 4000)
        self.store.save_reader_feedback("003", 0.42, 0.58, 3800)
        self.store.save_reader_feedback("004", 0.40, 0.59, 3700)

        prompt_crisis = agent._build_prompt(brief)
        self.assertIn("🚨 读者流失危机节奏补偿指令", prompt_crisis)
        self.assertIn("重度危机", prompt_crisis)
        self.assertIn("【重度危机补偿】", prompt_crisis)

    def test_writer_agent_style_prompt(self):
        # 1. 写入绑定的平台 meta 信息（晋江）
        meta_data = {"platform": "jinjiang"}
        self.meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

        # 2. 实例化 WriterAgent 并挂载属性
        writer = WriterAgent(llm=None)
        writer.project_dir = self.tmpdir

        style_prompt = writer._get_platform_style()
        self.assertIn("晋江文学城", style_prompt)
        self.assertIn("文字优美细腻", style_prompt)
        self.assertIn("文笔红线/避坑规避", style_prompt)
        self.assertIn("严禁主角人设扁平无脑化", style_prompt)


if __name__ == "__main__":
    unittest.main()
