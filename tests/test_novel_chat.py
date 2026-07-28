import json
import unittest

from web.novel_chat import NovelChatHandler
from web.models import NovelChatRequest


class QueueLLM:
    def __init__(self, *responses):
        self.responses = list(responses)

    def generate(self, _agent, _prompt):
        return json.dumps(self.responses.pop(0), ensure_ascii=False)


class NovelChatHandlerTests(unittest.TestCase):
    def test_request_model_accepts_deep_planning_steps(self):
        request = NovelChatRequest(step=10, user_input="确认终局", context={})

        self.assertEqual(request.step, 10)

    def test_step2_collects_reader_promise_before_protagonist(self):
        handler = NovelChatHandler(QueueLLM({
            "logline": "她必须在七天内找出城市停电的真相。",
            "target_reader": "偏爱都市悬疑的读者",
            "emotional_experience": ["紧张", "解谜"],
            "core_appeals": ["限时危机", "层层反转"],
            "follow_up": "谁最适合被卷入这场危机？",
        }))

        result = handler.handle_step(2, "希望读者一直猜真相。", {"theme": "全城停电"})

        self.assertEqual(result["step"], 3)
        self.assertEqual(result["context"]["reader_promise"]["core_appeals"], ["限时危机", "层层反转"])
        self.assertIn("谁最适合", result["ai_message"])

    def test_step5_collects_serial_engine_and_generates_summary_card(self):
        handler = NovelChatHandler(QueueLLM(
            {
                "progression_path": ["追查街区", "揭开城市系统"],
                "story_loop": "每次恢复一区供电，就暴露一层幕后真相。",
                "suspense_sources": ["停电倒计时"],
                "milestone_goals": ["恢复医院供电"],
            },
            {
                "title_suggestions": ["黑灯之后"],
                "logline": "停电七日，真相逐区亮起。",
                "genre_positioning": "都市悬疑",
                "target_reader": "悬疑读者",
                "reader_promise": ["解谜"],
                "tone": "紧张",
            },
        ))

        result = handler.handle_step(5, "逐区恢复供电并揭开真相。", {"theme": "全城停电"})

        self.assertEqual(result["step"], 6)
        self.assertTrue(result["basic_ready"])
        self.assertEqual(result["context"]["serial_engine"]["story_loop"], "每次恢复一区供电，就暴露一层幕后真相。")
        self.assertEqual(result["card"]["title_suggestions"], ["黑灯之后"])

    def test_step6_normalizes_card_and_can_finish_without_deep_planning(self):
        handler = NovelChatHandler(QueueLLM())
        payload = {
            "action": "create",
            "card": {"title_suggestions": ["黑灯之后"], "logline": "停电七日。"},
            "target_chapters": 80,
            "target_chars": [1800, 2600],
            "scale": "medium",
            "scale_label": "中篇小说",
        }

        result = handler.handle_step(6, json.dumps(payload, ensure_ascii=False), {})

        self.assertTrue(result["done"])
        self.assertEqual(result["context"]["chosen_title"], "黑灯之后")
        self.assertEqual(result["context"]["summary_card"]["logline"], "停电七日。")
        self.assertEqual(result["context"]["target_chapters"], 80)

    def test_step6_can_enter_deep_planning(self):
        handler = NovelChatHandler(QueueLLM())

        result = handler.handle_step(6, json.dumps({"action": "deep", "card": {}}, ensure_ascii=False), {})

        self.assertFalse(result["done"])
        self.assertEqual(result["step"], 7)
        self.assertIn("角色关系", result["ai_message"])

    def test_step10_completes_deep_planning_and_returns_to_finalization(self):
        handler = NovelChatHandler(QueueLLM({
            "opening_event": "城市突然停电。",
            "midpoint_escalation": "主角发现供电系统会吞噬记忆。",
            "major_reversal": "盟友才是系统维护者。",
            "ending_direction": "主角公开真相并重建城市。",
        }))

        result = handler.handle_step(10, "最后让主角公开真相。", {"summary_card": {"title_suggestions": ["黑灯之后"]}})

        self.assertEqual(result["step"], 6)
        self.assertTrue(result["deep_complete"])
        self.assertTrue(result["basic_ready"])
        self.assertFalse(result["done"])
        self.assertEqual(result["context"]["turning_points"]["major_reversal"], "盟友才是系统维护者。")

    def test_full_base_and_deep_flow_returns_normalized_blueprint(self):
        handler = NovelChatHandler(QueueLLM(
            {"theme": "全城停电", "genre": "都市悬疑", "keywords": ["停电"], "follow_up": "读者期待什么？"},
            {"logline": "停电七日追查真相。", "target_reader": "悬疑读者", "emotional_experience": ["紧张"], "core_appeals": ["解谜"], "follow_up": "主角是谁？"},
            {"protagonist": {"name": "林灯", "identity": "电力工程师"}, "follow_up": "阻力是什么？"},
            {"conflict": "供电系统隐藏真相", "external_opposition": ["幕后组织"], "relationship_tensions": [], "world_rules": ["每恢复一区供电就失去一段记忆"], "stakes": "城市永久停摆", "follow_up": "如何持续产生剧情？"},
            {"progression_path": ["恢复街区供电"], "story_loop": "逐区恢复供电并揭露秘密", "suspense_sources": ["倒计时"], "milestone_goals": ["恢复医院"]},
            {"title_suggestions": ["黑灯之后"], "logline": "停电七日追查真相。", "genre_positioning": "都市悬疑", "target_reader": "悬疑读者", "reader_promise": ["解谜"], "tone": "紧张"},
            {"characters": [{"name": "周岚", "role": "盟友", "relationship": "同事", "tension": "隐瞒秘密"}], "relationship_hooks": ["盟友秘密"], "follow_up": "成长如何变化？"},
            {"capability_arc": ["掌握系统"], "identity_arc": ["工程师到守护者"], "emotional_arc": ["从自保到担当"], "escalating_costs": ["失去记忆"], "follow_up": "如何分卷？"},
            {"volumes": [{"title": "暗城", "goal": "恢复医院", "conflict": "资源争夺", "climax": "医院亮灯", "ending_hook": "发现系统秘密"}], "follow_up": "关键转折是什么？"},
            {"opening_event": "城市突然停电", "midpoint_escalation": "系统吞噬记忆", "major_reversal": "盟友参与维护系统", "ending_direction": "公开真相"},
        ))
        context = {}
        for step, user_input in (
            (1, "全城停电"),
            (2, "持续解谜"),
            (3, "电力工程师林灯"),
            (4, "幕后组织阻止恢复供电"),
            (5, "逐区恢复供电"),
        ):
            result = handler.handle_step(step, user_input, context)
            context = result["context"]
        result = handler.handle_step(6, json.dumps({"action": "deep", "card": context["summary_card"]}, ensure_ascii=False), context)
        context = result["context"]
        for step, user_input in ((7, "盟友隐瞒秘密"), (8, "代价递增"), (9, "三卷推进"), (10, "最终公开真相")):
            result = handler.handle_step(step, user_input, context)
            context = result["context"]

        self.assertEqual(result["step"], 6)
        self.assertTrue(result["deep_complete"])
        self.assertEqual(context["summary_card"]["title_suggestions"], ["黑灯之后"])
        self.assertEqual(context["serial_engine"]["story_loop"], "逐区恢复供电并揭露秘密")
        self.assertEqual(context["volume_skeleton"]["volumes"][0]["title"], "暗城")


if __name__ == "__main__":
    unittest.main()
