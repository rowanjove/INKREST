import unittest
from novel_agent.quality.style_rules import (
    check_ai_style,
    check_anti_ai_flavor,
    check_paragraph_layout,
)
from novel_agent.quality.scene_delta import check_scene_delta
from novel_agent.quality.hooks import extract_tail_hooks, check_head_continuity


class TestStyleRules(unittest.TestCase):
    def test_check_ai_style_empty(self):
        res = check_ai_style("")
        self.assertTrue(res["pass"])
        self.assertEqual(res["score"], 100)
        self.assertEqual(res["details"], [])
        self.assertEqual(res["total_hits"], 0)

    def test_check_ai_style_clean(self):
        text = "林澈推开木门，看到师父坐在桌前喝茶。窗外的风吹了进来，十分凉爽。"
        res = check_ai_style(text)
        self.assertTrue(res["pass"])
        self.assertEqual(res["score"], 100)
        self.assertEqual(res["total_hits"], 0)

    def test_check_ai_style_hits(self):
        # 包含：嘴角微微上扬，深吸一口气，心中暗道
        text = (
            "林澈嘴角微微上扬。他深吸一口气，心中暗道：“这一切终于开始了。”"
            "看到敌人退去，他不禁松了一口气。竟然有人敢来挑衅，他居然没有察觉。"
        )
        res = check_ai_style(text)
        # 命中密度高时应当降低 score
        self.assertLess(res["score"], 100)
        self.assertGreater(res["total_hits"], 3)
        self.assertTrue(any("嘴角微微上扬" in d for d in res["details"]))
        self.assertTrue(any("深吸一口气" in d for d in res["details"]))

    def test_check_anti_ai_flavor_empty(self):
        res = check_anti_ai_flavor("")
        self.assertTrue(res["pass"])
        self.assertEqual(res["score"], 100)
        self.assertEqual(res["ending_type"], "empty")

    def test_check_anti_ai_flavor_hits(self):
        # 对话字数 >= 24，且有情绪直写(感到愤怒)和抽象氛围词(气氛十分凝固)
        text = (
            "林澈感到愤怒，这里的气氛十分凝固。他转过头说道：“我们不能再这样等下去了，"
            "敌人的脚步声已经越来越近，如果还不采取行动就彻底来不及了。”"
        )
        res = check_anti_ai_flavor(text)
        self.assertLess(res["score"], 100)
        self.assertGreater(res["emotion_telling_hits"], 0)
        self.assertGreater(res["abstract_modifier_hits"], 0)
        self.assertGreater(res["dialogue_overcomplete_hits"], 0)

    def test_check_anti_ai_flavor_endings(self):
        # 1. bad ending: 望着夜色感慨
        text_bad = "他望着远方的夜色，心中充满了复杂与感慨。"
        res_bad = check_anti_ai_flavor(text_bad)
        self.assertEqual(res_bad["ending_type"], "bad")
        self.assertFalse(res_bad["pass"])  # level 不在 none 或 warning 内

        # 2. hook ending: 响了/门开了/灯灭了
        text_hook = "正当他准备休息时，门外突然传来了枪声。"
        res_hook = check_anti_ai_flavor(text_hook)
        self.assertEqual(res_hook["ending_type"], "hook")
        self.assertTrue(res_hook["pass"])

        # 3. neutral ending
        text_neutral = "林澈关上了抽屉，坐在椅子上静静等待。"
        res_neutral = check_anti_ai_flavor(text_neutral)
        self.assertEqual(res_neutral["ending_type"], "neutral")

    def test_check_paragraph_layout(self):
        # 测试短段落
        text_short = "第一段很短。\n第二段也很短。"
        res_short = check_paragraph_layout(text_short)
        self.assertTrue(res_short["pass"])
        self.assertEqual(res_short["score"], 100)
        self.assertEqual(res_short["long_paragraphs"], 0)

        # 测试含有超过 150 字的段落
        long_para = "林" * 160
        text_long = f"正常段落。\n{long_para}\n正常段落二。"
        res_long = check_paragraph_layout(text_long, max_chars=150)
        self.assertEqual(res_long["long_paragraphs"], 1)
        self.assertEqual(res_long["total_paragraphs"], 3)
        self.assertLess(res_long["score"], 100)


class TestSceneDelta(unittest.TestCase):
    def test_check_scene_delta_empty(self):
        res = check_scene_delta("")
        self.assertFalse(res["pass"])
        self.assertEqual(res["score"], 0)

    def test_check_scene_delta_action(self):
        # 富含动作词：走、跑、拿、推、打、开门
        text = (
            "林澈快步走出房间，在走廊里飞奔。他冲入楼梯口，一把推开木门。\n\n"
            "他拿起桌上的笔，扔了出去，然后关上门，飞速离开现场。"
        )
        res = check_scene_delta(text)
        self.assertTrue(res["pass"])
        self.assertGreater(res["action_count"], res["static_count"])
        self.assertGreaterEqual(res["score"], 70)

    def test_check_scene_delta_static(self):
        # 富含内心戏：想、思考、心里、回忆、沉思
        text = (
            "林澈站在窗前开始琢磨。他在心里默默回忆着昨晚发生的事，沉思良久。\n\n"
            "他觉得这件事情透露着莫名其妙，认为应该重新思考，心里隐隐觉得不安。"
        )
        res = check_scene_delta(text)
        # 静态词比例太高时，动作感极弱，分数较低且有效场景数会受到限制
        self.assertLess(res["score"], 70)
        self.assertEqual(res["valid_scenes"], 0)
        self.assertGreater(res["static_count"], res["action_count"])


class TestHooks(unittest.TestCase):
    def test_extract_tail_hooks(self):
        # 构造包含了 unfinished_action(刚准备)、injury(伤口流血)、perception(注意到) 的尾部文本
        text = (
            "前面的无关描写。\n林澈的伤口正在流血，他感到一阵剧烈的疼痛。"
            "当他走近桌子时，突然注意到地上的脚印。他刚准备弯腰去捡，突然听到后方传来敲门声。"
        )
        res = extract_tail_hooks(text, tail_chars=500)
        self.assertIn("伤口", res["injuries"])
        self.assertIn("流血", res["injuries"])
        self.assertTrue(any("脚印" in p or "注意到" in p for p in res["perceptions"]))
        self.assertTrue(any("弯腰" in a or "刚准备" in a for a in res["unfinished_actions"]))
        self.assertGreater(len(res["keywords"]), 0)

    def test_check_head_continuity(self):
        prev_hooks = {
            "unfinished_actions": ["刚准备弯腰去捡"],
            "injuries": ["伤口流血"],
            "perceptions": ["注意到脚印"],
        }
        # 1. 完美继承：头部的 700 字内包含了所有的 hooks 描述
        text_pass = "林澈强忍着伤口流血的剧痛。他刚准备弯腰去捡那枚硬币，同时注意到脚印的延伸方向。"
        res_pass = check_head_continuity(prev_hooks, text_pass, head_chars=700)
        self.assertTrue(res_pass["pass"])
        self.assertEqual(res_pass["score"], 1.0)
        self.assertEqual(res_pass["missing_hooks"], [])

        # 2. 丢失 hooks 扣分：只包含了“伤口流血”，丢了“刚准备弯腰去捡”和“注意到脚印”
        text_fail = "林澈觉得伤口流血止住了，他决定上楼睡觉。"
        res_fail = check_head_continuity(prev_hooks, text_fail, head_chars=700)
        self.assertFalse(res_fail["pass"])
        self.assertLess(res_fail["score"], 0.65)
        self.assertEqual(len(res_fail["missing_hooks"]), 2)


if __name__ == "__main__":
    unittest.main()
