"""Chapter Planner Agent — expands a chapter brief into a detailed synopsis."""

import json
from typing import Any, Dict

from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.chapter_planner")


class ChapterPlannerAgent(PromptAgent):
    """Expands a chapter brief from ManagingEditor into a detailed synopsis
    with beats, character intents, and foreshadow plans."""

    def __init__(self, llm, prompts=None):
        super().__init__("chapter_planner", llm)
        self.prompts = prompts
        self.project_dir = None
        self.store = None

    def _build_prompt(
        self, chapter_brief: Dict[str, Any], runtime_context: str = ""
    ) -> str:
        template = self.prompts.load("chapter_planner") if self.prompts else ""
        
        # 1. 加载平台预设
        platform_name = "qidian"
        if self.project_dir:
            meta_path = self.project_dir / "config" / "project_meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    platform_name = meta.get("platform", "qidian")
                except Exception:
                    pass
        
        from novel_agent.control.platform_profiles import resolve_platform_profile
        profile = resolve_platform_profile(platform_name)
        
        platform_constraints = [
            f"目标平台：{profile['label']}",
            f"写作风格建议：{profile['style_prompt']}",
            "避坑与红线规则："
        ]
        for rule in profile.get("rules_blacklist", []):
            platform_constraints.append(f"- {rule}")
            
        platform_prompt_str = "\n".join(platform_constraints)
        
        # 1.5 加载全局世界观与人物设定
        global_assets_str = ""
        if self.project_dir:
            try:
                world_path = self.project_dir / "assets" / "world_bible.md"
                char_path = self.project_dir / "assets" / "character_cards.yaml"
                assets_parts = []
                if world_path.exists():
                    assets_parts.append(f"### 核心世界观与设定参考\n{world_path.read_text(encoding='utf-8').strip()}")
                if char_path.exists():
                    assets_parts.append(f"### 核心角色设定卡参考\n{char_path.read_text(encoding='utf-8').strip()}")
                if assets_parts:
                    global_assets_str = "## 全局小说背景与设定\n请在符合并严格延续以下小说世界观、时代背景与核心人物特征的前提下进行本章详细剧情规划，切勿偏离原本的题材（如将网游电竞题材写成仙侠或科幻）：\n\n" + "\n\n".join(assets_parts)
            except Exception as e:
                logger.warning("Failed to load global assets in chapter planner: %s", e)
        
        # 2. 黄金三章硬性约束
        chapter_id = chapter_brief.get("chapter_id", "001")
        golden_prompt_str = ""
        try:
            ch_num = int(chapter_id)
        except (ValueError, TypeError):
            ch_num = 1
            
        if ch_num in (1, 2, 3):
            golden_prompt_str = f"## 黄金三章专项质量规则 (本章为第 {ch_num} 章)\n本章属于全书签约与留存最核心的前三章。请严格执行以下该平台黄金三章指导：\n{profile['golden_three_rules']}"

        # 3. 读者反馈自适应（节奏补偿）
        feedback_prompt_str = ""
        if self.store:
            try:
                recent = self.store.get_recent_feedback(limit=3)
                if recent:
                    avg_bounce = sum(r.get("bounce_rate", 0.0) for r in recent) / len(recent)
                    if avg_bounce >= 0.25:
                        if avg_bounce > 0.35:
                            level = "重度危机"
                            comp = "【重度危机补偿】：严禁任何无意义的日常、大段景色与设定描写，本章大纲规划必须立刻引爆核心的戏剧性反击、打脸或高潮反转！快速拉满读者的爽感与情绪张力，重塑强烈的追读期待。"
                        else:
                            level = "中度危机"
                            comp = "【中度危机补偿】：本章应适当精简环境铺垫，尽快引入一个小爆点、金手指的功效验证，或者爆发一个局部的戏剧性矛盾冲突。"
                        feedback_prompt_str = f"## 🚨 读者流失危机节奏补偿指令\n系统检测到近几章读者的平均跳出率为 {avg_bounce*100:.1f}%，处于【{level}】状态！\n请执行以下补偿方案：\n{comp}"
            except Exception as e:
                logger.error("Error computing adaptive pacing feedback: %s", e)

        # 拼接最终 prompt
        extended_sections = []
        if global_assets_str:
            extended_sections.append(global_assets_str)
        if platform_prompt_str:
            extended_sections.append(f"## 平台风格与避坑约束\n{platform_prompt_str}")
        if golden_prompt_str:
            extended_sections.append(golden_prompt_str)
        if feedback_prompt_str:
            extended_sections.append(feedback_prompt_str)
        if runtime_context:
            extended_sections.append(
                f"## 体量与规划约束\n{runtime_context}"
            )

        extended_prompt = "\n\n".join(extended_sections)
        input_json = json.dumps(chapter_brief, ensure_ascii=False, indent=2)
        
        if extended_prompt:
            return f"{template}\n\n{extended_prompt}\n\n## 输入\n{input_json}".strip()
        else:
            return f"{template}\n\n## 输入\n{input_json}".strip()

    def _parse_and_validate_expansion(self, raw: str, chapter_brief: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = loads_json_object(raw)
            result = self._validate(result, chapter_brief)
            return result
        except Exception as exc:
            logger.error("Failed to parse chapter planner output: %s", exc)
            return self._fallback(chapter_brief)

    def expand(
        self, chapter_brief: Dict[str, Any], runtime_context: str = ""
    ) -> Dict[str, Any]:
        """Expand a chapter brief into a detailed synopsis."""
        prompt = self._build_prompt(chapter_brief, runtime_context)
        raw = self.run(prompt)
        return self._parse_and_validate_expansion(raw, chapter_brief)

    async def aexpand(
        self, chapter_brief: Dict[str, Any], runtime_context: str = ""
    ) -> Dict[str, Any]:
        """Expand a chapter brief into a detailed synopsis asynchronously."""
        prompt = self._build_prompt(chapter_brief, runtime_context)
        raw = await self.arun(prompt)
        return self._parse_and_validate_expansion(raw, chapter_brief)

    def _validate(
        self, result: Dict[str, Any], brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and fill defaults."""
        chapter_id = brief.get("chapter_id", "001")
        result.setdefault("chapter_id", chapter_id)
        result.setdefault("chapter_title", brief.get("chapter_title", ""))
        result.setdefault("detailed_synopsis", brief.get("chapter_goal", ""))

        # Validate beats
        beats = result.get("beats", [])
        if not beats or not isinstance(beats, list):
            result["beats"] = [{
                "beat_id": "B01",
                "function": "开场",
                "content": brief.get("chapter_goal", ""),
                "state_change": "",
            }]
        else:
            for i, beat in enumerate(beats):
                if isinstance(beat, dict):
                    beat.setdefault("beat_id", f"B{i + 1:02d}")
                    beat.setdefault("function", "推进")
                    beat.setdefault("content", "")
                    beat.setdefault("state_change", "")

        result.setdefault("character_intents", [])
        result.setdefault("foreshadow_plan", [])

        # Ensure handoff exists
        handoff = result.get("handoff_to_scene_planner", {})
        if not isinstance(handoff, dict):
            handoff = {}
        handoff.setdefault("must_include", brief.get("must_include", []))
        handoff.setdefault("must_not_include", brief.get("must_not_include", []))
        result["handoff_to_scene_planner"] = handoff

        return result

    def _fallback(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Return a minimal valid expansion when LLM fails."""
        chapter_id = brief.get("chapter_id", "001")
        goal = brief.get("chapter_goal", "推进剧情")
        return {
            "chapter_id": chapter_id,
            "chapter_title": brief.get("chapter_title", f"第 {chapter_id} 章"),
            "detailed_synopsis": goal,
            "beats": [
                {
                    "beat_id": "B01",
                    "function": "开场",
                    "content": f"进入本章场景，{goal}",
                    "state_change": "初始",
                },
                {
                    "beat_id": "B02",
                    "function": "冲突",
                    "content": "主要冲突展开",
                    "state_change": "升级",
                },
                {
                    "beat_id": "B03",
                    "function": "钩子",
                    "content": brief.get("hook", "留下悬念"),
                    "state_change": brief.get("output_state", "待定"),
                },
            ],
            "character_intents": [],
            "foreshadow_plan": [],
            "handoff_to_scene_planner": {
                "must_include": brief.get("must_include", []),
                "must_not_include": brief.get("must_not_include", []),
            },
        }
