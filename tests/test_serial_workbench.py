# -*- coding: utf-8 -*-
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from novel_agent.control.serial_engine import (
    generate_virtual_comments,
    compute_adaptive_outline,
)


class MockStore:
    def __init__(self, feedback_list=None):
        self.feedback_list = feedback_list or []

    def get_recent_feedback(self, limit=3):
        return self.feedback_list[:limit]


class MockLLM:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_prompt = ""

    def generate(self, role, prompt):
        self.last_prompt = prompt
        return self.response_text


class SerialWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-serial-test-"))
        self.ws_dir = self.tmpdir / "workspace"
        self.ws_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入默认的 outline.json
        self.outline_data = {
            "chosen_title": "测试小说",
            "core_theme": "电竞重建自我",
            "genre": "游戏",
            "genre_positioning": "电子竞技",
            "protagonist": {
                "name": "苏醒",
                "identity": "前职业选手",
                "edge": "退役战神系统"
            },
            "conflict": "击败宿敌战队夺冠",
            "world_rules": ["力量等级1", "力量等级2"]
        }
        (self.ws_dir / "outline.json").write_text(
            json.dumps(self.outline_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 写入分卷 arc_1.json
        self.arc_data = {
            "arc_id": "arc_1",
            "chapters": [
                {
                    "chapter_id": "001",
                    "chapter_title": "第一章 重回旧地",
                    "chapter_goal": "主角回俱乐部",
                    "detailed_synopsis": "主角重返被解约的战队基地。",
                    "handoff_to_scene_planner": {
                        "must_include": ["基地"],
                        "must_not_include": ["眼泪"]
                    }
                },
                {
                    "chapter_id": "002",
                    "chapter_title": "第二章 系统降临",
                    "chapter_goal": "系统觉醒",
                    "detailed_synopsis": "主角绑定系统并在路人局大显身手。",
                    "handoff_to_scene_planner": {
                        "must_include": ["系统"],
                        "must_not_include": []
                    }
                },
                {
                    "chapter_id": "003",
                    "chapter_title": "第三章 惊人首秀",
                    "chapter_goal": "打服青训队员",
                    "detailed_synopsis": "在训练赛里主角力挽狂澜击败青训王牌。",
                    "handoff_to_scene_planner": {
                        "must_include": ["训练赛"],
                        "must_not_include": []
                    }
                }
            ]
        }
        (self.ws_dir / "arc_1.json").write_text(
            json.dumps(self.arc_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 模拟生成章节目录
        self.chapters_dir = self.ws_dir / "chapters"
        self.chapters_dir.mkdir(parents=True, exist_ok=True)
        
        # 章节 001 已经生成 final.txt
        ch1_dir = self.chapters_dir / "chapter_001"
        ch1_dir.mkdir(parents=True, exist_ok=True)
        (ch1_dir / "chapter_final.txt").write_text(
            "这里是第一章的正式正文内容，字数比较多。苏醒回到了曾经奋斗过的战队基地，心中百感交集。"
            "当年的那些热血、那些拼搏，在一瞬间全部涌上心头。虽然他已经被战队解约，但是退役战神系统已经觉醒！"
            "从这一刻起，没有人可以阻挡他重返职业赛场的巅峰！这里是凑字数的一部分，用来确保章节字符数大于100个汉字。",
            encoding="utf-8"
        )
        (ch1_dir / "plan.json").write_text(
            json.dumps({"chapter_title": "第一章 重回旧地"}, ensure_ascii=False),
            encoding="utf-8"
        )

        # 章节 002 & 003 还没生成（没有 final.txt）

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_virtual_comments_generation_based_on_bounce_rate(self):
        # 1. 正常/低跳出率 -> 正面评论
        comments_pos = generate_virtual_comments("001", 0.15)
        self.assertEqual(len(comments_pos), 3)
        for c in comments_pos:
            self.assertIn("c_001_", c["id"])
            self.assertIn("⭐", c["rating"])
            self.assertGreaterEqual(len(c["rating"]), 4) # 正面应该是 4-5 星

        # 2. 中等跳出率 -> 中立评论
        comments_neu = generate_virtual_comments("001", 0.30)
        self.assertEqual(len(comments_neu), 3)
        ratings = [len(c["rating"]) for c in comments_neu]
        self.assertTrue(any(r == 3 or r == 4 for r in ratings))

        # 3. 高跳出率 -> 吐槽评论
        comments_neg = generate_virtual_comments("001", 0.40)
        self.assertEqual(len(comments_neg), 3)
        for c in comments_neg:
            self.assertTrue(len(c["rating"]) <= 2) # 吐槽应该是 1-2 星
            self.assertTrue(any(kw in c["content"] for kw in ["毒", "憋屈", "注水", "弃书"]))

    def test_compute_adaptive_outline_trigger(self):
        # 模拟有重度危机（平均跳出率 0.40）
        store = MockStore([
            {"chapter_id": "001", "bounce_rate": 0.40},
            {"chapter_id": "001", "bounce_rate": 0.40}
        ])
        
        # 纠偏期望重写的结果
        rewritten_chapters = [
            {
                "chapter_id": "002",
                "chapter_title": "第二章 战神归来",
                "detailed_synopsis": "【整改】：主角立刻开启系统，在大战中狂虐反派，爽点拉满。"
            },
            {
                "chapter_id": "003",
                "chapter_title": "第三章 惊人首秀",
                "detailed_synopsis": "【整改】：训练赛中爆砍五杀，震惊全场。"
            }
        ]
        llm = MockLLM(json.dumps(rewritten_chapters, ensure_ascii=False))

        # 1. 运行自适应纠偏
        old_ch, new_ch = compute_adaptive_outline(self.tmpdir, store, llm)
        
        # 2. 验证返回的章节是否为尚未生成的章节 (即 002 和 003)
        self.assertEqual(len(old_ch), 2)
        self.assertEqual(old_ch[0]["chapter_id"], "002")
        self.assertEqual(old_ch[1]["chapter_id"], "003")

        self.assertEqual(len(new_ch), 2)
        self.assertEqual(new_ch[0]["chapter_title"], "第二章 战神归来")

        # 3. 验证主编指令里包含了“重度流失警告”的关键词
        self.assertIn("【重度流失警告】", llm.last_prompt)

    def test_apply_adaptive_outline_rewrites_files(self):
        # 模拟在 projects.py 里的 apply_adaptive_outline 物理落库逻辑
        new_chapters = [
            {
                "chapter_id": "002",
                "chapter_title": "纠偏后的第二章",
                "detailed_synopsis": "绑定外挂光速打脸剧情",
                "handoff_to_scene_planner": {
                    "must_include": ["系统", "爽点打脸"],
                    "must_not_include": ["拖延"]
                }
            }
        ]

        # projects.py 中核心实现的应用逻辑
        new_map = {ch["chapter_id"]: ch for ch in new_chapters if "chapter_id" in ch}
        arc_files = sorted(list(self.ws_dir.glob("arc_*.json")))
        
        for arc_file in arc_files:
            arc_data = json.loads(arc_file.read_text(encoding="utf-8"))
            modified = False
            for ch in arc_data.get("chapters", []):
                ch_id = ch.get("chapter_id")
                if ch_id in new_map:
                    new_val = new_map[ch_id]
                    ch["title"] = new_val.get("chapter_title", ch.get("title", ""))
                    ch["goal"] = new_val.get("chapter_goal", new_val.get("detailed_synopsis", ch.get("goal", "")))
                    ch["must_include"] = new_val.get("handoff_to_scene_planner", {}).get("must_include", ch.get("must_include", []))
                    ch["must_not_include"] = new_val.get("handoff_to_scene_planner", {}).get("must_not_include", ch.get("must_not_include", []))
                    modified = True
            if modified:
                arc_file.write_text(json.dumps(arc_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 验证 arc_1.json 已经成功落库物理修改
        updated_arc = json.loads((self.ws_dir / "arc_1.json").read_text(encoding="utf-8"))
        ch002 = [ch for ch in updated_arc["chapters"] if ch["chapter_id"] == "002"][0]
        
        self.assertEqual(ch002["title"], "纠偏后的第二章")
        self.assertEqual(ch002["goal"], "绑定外挂光速打脸剧情")
        self.assertEqual(ch002["must_include"], ["系统", "爽点打脸"])
        self.assertEqual(ch002["must_not_include"], ["拖延"])

    def test_export_serial_format_all_chapters(self):
        # 物理模拟已生成多个章节
        ch2_dir = self.chapters_dir / "chapter_002"
        ch2_dir.mkdir(parents=True, exist_ok=True)
        (ch2_dir / "chapter_final.txt").write_text("这里是第二章的终极内容。", encoding="utf-8")
        (ch2_dir / "plan.json").write_text(json.dumps({"chapter_title": "第二章 系统现身"}), encoding="utf-8")

        # 提取已生成的章节数据列表（模拟 projects.py 的逻辑）
        chapters = []
        for ch_dir in sorted(list(self.chapters_dir.glob("chapter_*")), key=lambda d: d.name):
            ch_id = ch_dir.name.replace("chapter_", "")
            txt_path = ch_dir / "chapter_final.txt"
            plan_path = ch_dir / "plan.json"
            
            title = f"第 {ch_id} 章"
            if plan_path.exists():
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                title = plan.get("chapter_title", title)
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8").strip()
                chapters.append((ch_id, title, text))

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0][0], "001")
        self.assertEqual(chapters[1][1], "第二章 系统现身")

        # 1. 验证 TXT 缝合导出
        txt_lines = []
        for ch_id, title, text in chapters:
            txt_lines.append(f"### {title}\n\n{text}\n\n")
        full_text = "\n".join(txt_lines)
        self.assertIn("### 第一章 重回旧地", full_text)
        self.assertIn("苏醒回到了曾经奋斗过的战队基地", full_text)
        self.assertIn("### 第二章 系统现身", full_text)
        self.assertIn("这里是第二章的终极内容。", full_text)

        # 2. 验证 ZIP 分章压缩包导出
        zip_path = self.tmpdir / "export.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ch_id, title, text in chapters:
                zf.writestr(f"chapter_{ch_id}_{title}.txt", text)

        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            self.assertEqual(len(namelist), 2)
            self.assertIn("chapter_001_第一章 重回旧地.txt", namelist)
            self.assertIn("chapter_002_第二章 系统现身.txt", namelist)
            
            ch1_content = zf.read("chapter_001_第一章 重回旧地.txt").decode("utf-8")
            self.assertIn("苏醒回到了曾经奋斗过的战队基地", ch1_content)


if __name__ == "__main__":
    unittest.main()
