import unittest
from novel_agent.quality.hard_rules import run_hard_rule_audit
from novel_agent.agents.auditor import AuditorAgent
from novel_agent.agents.base import StaticLLM


class TestHardRules(unittest.TestCase):
    def setUp(self):
        # 基础的 state
        self.state = {
            "characters": {
                "林澈": {"location": "沈府", "status": "健康"},
                "沈妙": {"location": "林府", "status": "健康"}
            },
            "objects": [
                {"id": "sword_01", "name": "龙泉剑", "holder": "林澈"},
                {"id": "book_01", "name": "无字天书", "holder": "沈妙"}
            ]
        }
        self.target_chars = [100, 300]
        self.sensitive_words = ["禁词一", "禁禁词"]

    def test_word_count_bounds(self):
        # 1. 正常字数
        text_normal = "林澈快步走出房间，在走廊里飞奔。他冲入楼梯口，一把推开木门。拿起桌上的笔，扔了出去，然后关上门，飞速离开现场。" * 4
        # 我们算一下中文字数
        issues = run_hard_rule_audit(
            final_text=text_normal,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update={}
        )
        # 应该没有字数相关的 issue
        self.assertFalse(any(i["type"] == "word_count_out_of_bounds" for i in issues))

        # 2. 字数过少
        text_short = "字数太少。"
        issues = run_hard_rule_audit(
            final_text=text_short,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update={}
        )
        word_issues = [i for i in issues if i["type"] == "word_count_out_of_bounds"]
        self.assertEqual(len(word_issues), 1)
        self.assertEqual(word_issues[0]["audit_class"], "CRITICAL")
        self.assertEqual(word_issues[0]["severity"], "high")

        # 3. 字数过多
        text_long = "林澈快步走出房间，在走廊里飞奔。他冲入楼梯口，一把推开木门。拿起桌上的笔，扔了出去，然后关上门，飞速离开现场。" * 20
        issues = run_hard_rule_audit(
            final_text=text_long,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update={}
        )
        word_issues = [i for i in issues if i["type"] == "word_count_out_of_bounds"]
        self.assertEqual(len(word_issues), 1)

    def test_sensitive_word_hits(self):
        # 命中敏感词
        text = "林澈觉得这件事情不对劲。\n这一行命中了禁词一。\n这是第三行。"
        issues = run_hard_rule_audit(
            final_text=text,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=self.sensitive_words,
            state_update={}
        )
        sensitive_issues = [i for i in issues if i["type"] == "sensitive_word_hit"]
        self.assertEqual(len(sensitive_issues), 1)
        self.assertEqual(sensitive_issues[0]["audit_class"], "CRITICAL")
        self.assertIn("行 2", sensitive_issues[0]["text"])
        self.assertEqual(sensitive_issues[0]["target_text"], "禁词一")

    def test_character_location_mismatch(self):
        # 计划中允许的位置
        plan = {
            "scenes": [
                {"location": "林府"},
                {"location": "沈府"}
            ]
        }
        
        # 1. 林澈历史在沈府，正文在林府活动，且没有在 state_update 中进行 location 的转移更新
        # 段落共现检测：一个段落里同时出现“林澈”和“林府”
        text_conflict = "林澈今天闲着无聊，来到了林府里喝茶叙旧。\n\n别的事情发生了。"
        issues = run_hard_rule_audit(
            final_text=text_conflict,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update={},
            plan=plan
        )
        loc_issues = [i for i in issues if i["type"] == "character_location_mismatch"]
        self.assertEqual(len(loc_issues), 1)
        self.assertEqual(loc_issues[0]["audit_class"], "CRITICAL")
        self.assertIn("林澈", loc_issues[0]["text"])

        # 2. 如果 state_update 中有该角色位置的更新，则不应该报错
        state_update = {
            "characters": {
                "林澈": {"location": "林府"}
            }
        }
        issues = run_hard_rule_audit(
            final_text=text_conflict,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update=state_update,
            plan=plan
        )
        loc_issues = [i for i in issues if i["type"] == "character_location_mismatch"]
        self.assertEqual(len(loc_issues), 0)

    def test_object_ownership_conflict(self):
        # 龙泉剑登记在林澈手里。正文段落中沈妙提到了龙泉剑，但 state_update 没有做所有权转移。
        text_conflict = "沈妙轻轻拔出了龙泉剑，剑光闪烁，寒气逼人。"
        issues = run_hard_rule_audit(
            final_text=text_conflict,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update={}
        )
        obj_issues = [i for i in issues if i["type"] == "object_ownership_conflict"]
        self.assertEqual(len(obj_issues), 1)
        self.assertEqual(obj_issues[0]["audit_class"], "CRITICAL")
        self.assertIn("龙泉剑", obj_issues[0]["text"])

        # 如果 state_update 中有所有权更新，则应当通过
        state_update_1 = {
            "objects": [
                {"id": "sword_01", "owner": "沈妙"}
            ]
        }
        issues_1 = run_hard_rule_audit(
            final_text=text_conflict,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update=state_update_1
        )
        obj_issues_1 = [i for i in issues_1 if i["type"] == "object_ownership_conflict"]
        self.assertEqual(len(obj_issues_1), 0)

        # 同样支持 holder 字段更新
        state_update_2 = {
            "objects": [
                {"id": "sword_01", "holder": "沈妙"}
            ]
        }
        issues_2 = run_hard_rule_audit(
            final_text=text_conflict,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=[],
            state_update=state_update_2
        )
        obj_issues_2 = [i for i in issues_2 if i["type"] == "object_ownership_conflict"]
        self.assertEqual(len(obj_issues_2), 0)

    def test_text_metrics_dialogue_ratio(self):
        # 1. 对话字数占比过高 (>65%)
        text_high_dialogue = "林澈说：“我们不能再等了，这次敌人的动作非常迅速，必须立即动手。”沈妙说：“没错，迟则生变，我们要快点。”"
        issues = run_hard_rule_audit(
            final_text=text_high_dialogue,
            state=self.state,
            target_chars=[50, 500],
            sensitive_words=[],
            state_update={}
        )
        ratio_issues = [i for i in issues if i["type"] == "excessive_dialogue"]
        self.assertEqual(len(ratio_issues), 1)
        self.assertEqual(ratio_issues[0]["audit_class"], "WARNING")
        self.assertEqual(ratio_issues[0]["severity"], "medium")

        # 2. 对话字数占比过低 (<15%)
        text_low_dialogue = "林澈快步走出房间，在走廊里飞奔。他冲入楼梯口，一把推开木门。拿起桌上的笔，扔了出去，然后关上门，飞速离开现场。"
        issues = run_hard_rule_audit(
            final_text=text_low_dialogue,
            state=self.state,
            target_chars=[50, 500],
            sensitive_words=[],
            state_update={}
        )
        ratio_issues = [i for i in issues if i["type"] == "deficient_dialogue"]
        self.assertEqual(len(ratio_issues), 1)
        self.assertEqual(ratio_issues[0]["audit_class"], "WARNING")
        self.assertEqual(ratio_issues[0]["severity"], "medium")

    def test_auditor_agent_integration(self):
        # 使用 StaticLLM 模拟大模型的返回。
        # 我们假设大模型只返回了低风险、没有问题的 audit report。
        mock_response = (
            "{\n"
            '  "risk_level": "低",\n'
            '  "issues": [],\n'
            '  "state_update": {\n'
            '    "events": [],\n'
            '    "objects": [],\n'
            '    "threads": [],\n'
            '    "characters": {}\n'
            '  },\n'
            '  "narrative_hooks": []\n'
            "}"
        )
        llm = StaticLLM({"auditor": mock_response})
        auditor = AuditorAgent(llm)

        # 传入的 chapter_text 会触发硬规则 CRITICAL（字数极少、或者带有敏感词）
        # 比如我们传一个极短且带敏感词的文本
        text = "字数少禁词一"
        
        result = auditor.audit(
            chapter_text=text,
            state=self.state,
            target_chars=self.target_chars,
            sensitive_words=self.sensitive_words,
            plan={}
        )

        # 1. 尽管大模型判定为低风险且无 issue，但是硬规则判定为 CRITICAL 且触发了 high 级 issue。
        # 因此，risk_level 必须被强制设为 "高"。
        self.assertEqual(result["risk_level"], "高")

        # 2. 检查 issues 中是否混入了硬规则的问题
        issues = result["issues"]
        self.assertTrue(any(i["type"] == "word_count_out_of_bounds" for i in issues))
        self.assertTrue(any(i["type"] == "sensitive_word_hit" for i in issues))

        # 3. 验证 audit_classification 等级分流
        classification = result["audit_classification"]
        self.assertIn("CRITICAL", classification)
        self.assertIn("WARNING", classification)
        self.assertIn("INFO", classification)
        
        # 字数超限、敏感词命中的 severity 是 high，所以它们应该被分流到 CRITICAL 列表中。
        critical_types = [i["type"] for i in classification["CRITICAL"]]
        self.assertIn("word_count_out_of_bounds", critical_types)
        self.assertIn("sensitive_word_hit", critical_types)


if __name__ == "__main__":
    unittest.main()
