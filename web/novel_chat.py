"""AI-guided novel creation blueprint handler.

The guide has a six-step default flow and an optional four-step deep-planning
flow. Each response returns the accumulated context so the frontend can render
an editable blueprint without maintaining a second data model.
"""

import json
from typing import Any, Dict

from novel_agent.agents.base import LLMClient
from novel_agent.json_utils import loads_json_object


_STEP_PROMPTS: Dict[int, str] = {
    1: """你是小说策划编辑。根据用户的故事灵感提取创意种子，输出纯 JSON：
{"theme":"核心主题","genre":"题材","keywords":["关键词"],"follow_up":"询问读者期待的问题"}""",
    2: """你是小说策划编辑。提炼读者为什么会点开并追读这个故事，输出纯 JSON：
{"logline":"一句话卖点","target_reader":"目标读者","emotional_experience":["情绪体验"],"core_appeals":["核心爽点或吸引力"],"follow_up":"询问主角的问题"}""",
    3: """你是小说策划编辑。提炼能持续推动剧情的主角引擎，输出纯 JSON：
{"protagonist":{"name":"姓名或待定","identity":"身份","desire":"核心欲望","dilemma":"当前困境","flaw":"缺陷","edge":"优势或金手指","cost":"代价","growth_direction":"成长方向"},"follow_up":"询问持续冲突的问题"}""",
    4: """你是小说策划编辑。提炼持续阻止主角的冲突舞台，输出纯 JSON：
{"conflict":"核心矛盾","external_opposition":["外部阻力"],"relationship_tensions":["关系矛盾"],"world_rules":["世界规则"],"stakes":"失败代价","follow_up":"询问连载发动机的问题"}""",
    5: """你是小说策划编辑。提炼故事如何持续产生新剧情，输出纯 JSON：
{"progression_path":["升级路径"],"story_loop":"可重复产生剧情的循环","suspense_sources":["悬念来源"],"milestone_goals":["阶段目标"]}""",
    6: """你是小说策划编辑。根据已有蓝图生成可编辑概要卡，输出纯 JSON：
{"title_suggestions":["三个书名候选"],"logline":"一句话卖点","genre_positioning":"类型定位","target_reader":"目标读者","reader_promise":["读者承诺"],"tone":"整体基调","similar_works":["可选参考作品"]}""",
    7: """你是小说策划编辑。提炼角色关系网，输出纯 JSON：
{"characters":[{"name":"角色名","role":"角色功能","relationship":"与主角关系","tension":"关系张力"}],"relationship_hooks":["可持续展开的关系钩子"],"follow_up":"询问成长变化的问题"}""",
    8: """你是小说策划编辑。提炼主角的多线成长轨迹，输出纯 JSON：
{"capability_arc":["能力变化"],"identity_arc":["身份变化"],"emotional_arc":["情感变化"],"escalating_costs":["递增代价"],"follow_up":"询问分卷方向的问题"}""",
    9: """你是小说策划编辑。提炼分卷骨架，输出纯 JSON：
{"volumes":[{"title":"卷名","goal":"阶段目标","conflict":"主要冲突","climax":"高潮","ending_hook":"结尾钩子"}],"follow_up":"询问关键转折的问题"}""",
    10: """你是小说策划编辑。提炼改变故事方向的关键转折，输出纯 JSON：
{"opening_event":"开局事件","midpoint_escalation":"中期升级","major_reversal":"重大反转","ending_direction":"终局方向"}""",
}


_STEP_INTROS: Dict[int, Dict[str, Any]] = {
    1: {
        "ai_message": "你好，我会作为策划编辑陪你把灵感整理成可写的作品蓝图。\n\n**先说说你想写一个什么样的故事？** 一个场景、一种感觉或一个设定都可以。",
        "suggestions": [
            "都市悬疑，主角能听到死者留下的最后一句话",
            "末世生存，文明崩塌后从一座小镇重建家园",
            "古代宅斗，女主接手濒临破产的家族生意",
        ],
    },
    2: {
        "suggestions": [
            "想让读者享受层层解谜和连续反转",
            "想突出升级成长，每隔几章都有明确收获",
            "想写人物关系拉扯，让读者期待感情变化",
        ],
    },
    3: {
        "suggestions": [
            "底层小人物，擅长抓住规则漏洞，但每次使用能力都要付出代价",
            "外表冷静的天才少女，真正想要的是摆脱家族安排",
            "失去记忆的退伍军人，必须在追杀中找回身份",
        ],
    },
    4: {
        "suggestions": [
            "主角的能力正是幕后组织长期追捕的目标",
            "表面盟友有自己的目的，合作越深风险越高",
            "世界规则本身会不断抬高主角获胜的代价",
        ],
    },
    5: {
        "suggestions": [
            "每解决一个局部危机，就暴露更大的幕后问题",
            "通过任务、升级和新地图持续产生阶段目标",
            "用关系变化和秘密揭露推动每一卷升级",
        ],
    },
    7: {
        "ai_message": "基础蓝图已经能建档。我们继续补强总纲。\n\n**先看角色关系网：哪些人会帮助、阻碍或改变主角？**",
        "suggestions": [
            "一个可靠但隐瞒关键秘密的盟友",
            "一个与主角目标一致、手段相反的竞争者",
            "一个迫使主角面对自身缺陷的亲密关系",
        ],
    },
    8: {
        "suggestions": [
            "能力越强，失去的私人生活越多",
            "从只想自保，到愿意承担更大的责任",
            "身份不断上升，但必须面对旧关系的疏离",
        ],
    },
    9: {
        "suggestions": [
            "先解决局部危机，再揭开幕后组织，最后挑战世界规则",
            "每卷更换舞台，但保留一条逐步逼近真相的主线",
            "每卷让主角得到一项收获，同时失去一项重要东西",
        ],
    },
    10: {
        "suggestions": [
            "中期揭示主角一直相信的前提其实是假的",
            "最可靠的盟友与幕后真相存在直接关系",
            "终局不是击败敌人，而是改变一条世界规则",
        ],
    },
}


class NovelChatHandler:
    """Manage the creation-guide blueprint state machine."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def get_intro(self, step: int) -> Dict[str, Any]:
        intro = _STEP_INTROS.get(step, {})
        return {
            "step": step,
            "ai_message": intro.get("ai_message", ""),
            "suggestions": intro.get("suggestions", []),
        }

    def handle_step(self, step: int, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if step < 1 or step > 10:
            return {"error": "Invalid step", "step": step}
        handler = {
            1: self._handle_seed,
            2: self._handle_reader_promise,
            3: self._handle_protagonist,
            4: self._handle_conflict_stage,
            5: self._handle_serial_engine,
            6: self._handle_finalize,
            7: self._handle_character_network,
            8: self._handle_growth_arcs,
            9: self._handle_volume_skeleton,
            10: self._handle_turning_points,
        }[step]
        return handler(user_input, context)

    def _extract(self, step: int, user_input: str, context: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        background = json.dumps(context, ensure_ascii=False, indent=2)
        prompt = f"{_STEP_PROMPTS[step]}\n\n已有蓝图：\n{background}\n\n用户说：{user_input}"
        try:
            return loads_json_object(self.llm.generate("novel_chat", prompt))
        except Exception:
            return fallback

    def _reply(self, step: int, ai_message: str, context: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
        return {
            "step": step,
            "ai_message": ai_message,
            "suggestions": _STEP_INTROS.get(step, {}).get("suggestions", []),
            "context": context,
            "done": False,
            **extra,
        }

    def _handle_seed(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(1, user_input, context, {
            "theme": user_input, "genre": "待定", "keywords": [], "follow_up": "",
        })
        context.update({
            "theme": data.get("theme", user_input),
            "genre": data.get("genre", "待定"),
            "keywords": data.get("keywords", []),
            "user_inspiration": user_input,
        })
        follow_up = data.get("follow_up") or "这个故事最想让读者获得什么体验？为什么会想继续追下去？"
        return self._reply(2, f"创意种子已经有了：**{context['theme']}**。\n\n{follow_up}", context)

    def _handle_reader_promise(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(2, user_input, context, {
            "logline": user_input, "target_reader": "待定", "emotional_experience": [], "core_appeals": [], "follow_up": "",
        })
        context["reader_promise"] = {
            "logline": data.get("logline", user_input),
            "target_reader": data.get("target_reader", "待定"),
            "emotional_experience": data.get("emotional_experience", []),
            "core_appeals": data.get("core_appeals", []),
        }
        follow_up = data.get("follow_up") or "接下来聚焦主角：谁最适合被卷入这个故事？他最想得到什么，又最怕失去什么？"
        return self._reply(3, f"读者期待已经明确：**{context['reader_promise']['logline']}**\n\n{follow_up}", context)

    def _handle_protagonist(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(3, user_input, context, {
            "protagonist": {"name": "待定", "identity": user_input}, "follow_up": "",
        })
        context["protagonist"] = data.get("protagonist", {"name": "待定", "identity": user_input})
        protagonist = context["protagonist"]
        follow_up = data.get("follow_up") or "什么力量会持续阻止主角？失败以后真正会失去什么？"
        return self._reply(4, f"主角引擎成立：**{protagonist.get('name', '主角')}**，{protagonist.get('identity', '')}。\n\n{follow_up}", context)

    def _handle_conflict_stage(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(4, user_input, context, {
            "conflict": user_input, "external_opposition": [user_input], "relationship_tensions": [],
            "world_rules": [], "stakes": "", "follow_up": "",
        })
        context["conflict_stage"] = {
            "conflict": data.get("conflict", user_input),
            "external_opposition": data.get("external_opposition", []),
            "relationship_tensions": data.get("relationship_tensions", []),
            "world_rules": data.get("world_rules", []),
            "stakes": data.get("stakes", ""),
        }
        follow_up = data.get("follow_up") or "最后补上连载发动机：故事靠什么不断产生新的目标、危机和悬念？"
        return self._reply(5, f"冲突舞台已经搭好：**{context['conflict_stage']['conflict']}**\n\n{follow_up}", context)

    def _handle_serial_engine(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(5, user_input, context, {
            "progression_path": [], "story_loop": user_input, "suspense_sources": [], "milestone_goals": [],
        })
        context["serial_engine"] = {
            "progression_path": data.get("progression_path", []),
            "story_loop": data.get("story_loop", user_input),
            "suspense_sources": data.get("suspense_sources", []),
            "milestone_goals": data.get("milestone_goals", []),
        }
        card = self._generate_summary_card(context)
        return self._reply(
            6,
            "基础蓝图已经整理完成。你可以调整卡片、体量和模板，然后直接创建；也可以继续完善总纲。",
            context,
            card=card,
            basic_ready=True,
        )

    def _generate_summary_card(self, context: Dict[str, Any]) -> Dict[str, Any]:
        reader = context.get("reader_promise", {})
        card = self._extract(6, "", context, {
            "title_suggestions": [f"《{context.get('theme', '未命名作品')}》"],
            "logline": reader.get("logline", context.get("theme", "")),
            "genre_positioning": context.get("genre", ""),
            "target_reader": reader.get("target_reader", "网文读者"),
            "reader_promise": reader.get("core_appeals", []),
            "tone": "",
            "similar_works": [],
        })
        context["summary_card"] = card
        return card

    def _handle_finalize(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            payload = json.loads(user_input) if isinstance(user_input, str) else user_input
        except (json.JSONDecodeError, TypeError):
            payload = {}
        card = payload.get("card") or context.get("summary_card", {})
        context["summary_card"] = card
        titles = card.get("title_suggestions", [])
        context["chosen_title"] = card.get("chosen_title") or (titles[0] if titles else "未命名作品")
        for key, default in (
            ("target_chapters", 200),
            ("target_chars", [2000, 3000]),
            ("scale", "long"),
            ("scale_label", "长篇小说"),
        ):
            context[key] = payload.get(key, context.get(key, default))
        if payload.get("preset_composition"):
            context["preset_composition"] = payload["preset_composition"]
        if payload.get("action") == "deep":
            intro = self.get_intro(7)
            return self._reply(7, intro["ai_message"], context)
        return {
            "step": 6,
            "ai_message": "作品蓝图已经确认，可以创建作品了。",
            "suggestions": [],
            "context": context,
            "done": True,
            "basic_ready": True,
            "deep_complete": bool(context.get("deep_complete")),
        }

    def _handle_character_network(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(7, user_input, context, {"characters": [], "relationship_hooks": [], "follow_up": ""})
        context["character_network"] = {
            "characters": data.get("characters", []),
            "relationship_hooks": data.get("relationship_hooks", []),
        }
        follow_up = data.get("follow_up") or "主角会经历哪些能力、身份和情感变化？代价如何逐步加重？"
        return self._reply(8, f"关系网已经补上。\n\n{follow_up}", context)

    def _handle_growth_arcs(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(8, user_input, context, {
            "capability_arc": [], "identity_arc": [], "emotional_arc": [], "escalating_costs": [], "follow_up": "",
        })
        context["growth_arcs"] = {
            "capability_arc": data.get("capability_arc", []),
            "identity_arc": data.get("identity_arc", []),
            "emotional_arc": data.get("emotional_arc", []),
            "escalating_costs": data.get("escalating_costs", []),
        }
        follow_up = data.get("follow_up") or "如果把故事拆成几个阶段，每一卷的目标、高潮和结尾钩子分别是什么？"
        return self._reply(9, f"成长轨迹清楚了。\n\n{follow_up}", context)

    def _handle_volume_skeleton(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(9, user_input, context, {"volumes": [], "follow_up": ""})
        context["volume_skeleton"] = {"volumes": data.get("volumes", [])}
        follow_up = data.get("follow_up") or "最后确认关键转折：什么事件真正开启故事，中期如何升级，最大反转是什么，终局走向哪里？"
        return self._reply(10, f"分卷骨架已经形成。\n\n{follow_up}", context)

    def _handle_turning_points(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        data = self._extract(10, user_input, context, {
            "opening_event": user_input, "midpoint_escalation": "", "major_reversal": "", "ending_direction": "",
        })
        context["turning_points"] = data
        context["deep_complete"] = True
        return self._reply(
            6,
            "深度规划完成。总纲草案已经并入作品蓝图，请最后确认后创建作品。",
            context,
            card=context.get("summary_card", {}),
            basic_ready=True,
            deep_complete=True,
        )
