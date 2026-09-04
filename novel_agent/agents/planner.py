import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.agents.base import PromptAgent
from novel_agent.control.chapter_window import VALID_DETAIL_LEVELS, VALID_SCENE_TYPES
from novel_agent.exceptions import LLMResponseError
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.planner")

# A malformed planner response is commonly caused by the model reaching its
# output limit or emitting a partial JSON document.  Retry exactly once at the
# planner boundary so transient format failures do not abort a whole chapter,
# while still keeping the failure bounded and visible to the caller.
_PLAN_PARSE_RETRIES = 1

ANTI_AI_MUST_NOT_INCLUDE = [
    "禁止直接写角色情绪",
    "禁止总结式、感慨式、决心式结尾",
    "禁止让角色用完整汇报式对话解释设定",
]


class PlannerAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("planner", llm)
        self.prompts = prompts

    def _build_prompt(
        self,
        chapter_id: str,
        chapter_goal: str,
        must_fix: Optional[List[Dict[str, Any]]] = None,
        duplicate_warnings: Optional[str] = None,
        foreshadow_recommendations: Optional[str] = None,
        runtime_context: Optional[str] = None,
        quality_rewrite_hints: Optional[str] = None,
        continuity_context: Optional[str] = None,
    ) -> str:
        template = self.prompts.load("planner") if self.prompts else ""
        prompt = (
            f"{template}\n\n"
            "请根据章节目标生成 JSON 章节计划。"
            f"\nchapter_id: {chapter_id}\nchapter_goal: {chapter_goal}"
        )
        if duplicate_warnings:
            prompt += (
                "\n\n## ⚠️ 【情节重复警告】\n"
                "检测到当前章节大纲与以下历史章节存在较高的语义相似度（可能有重复的情节或套路）。"
                "在规划本章场景时，请务必规避这些重复的情节，或做出足够新颖的差异化处理：\n"
                f"{duplicate_warnings}"
            )
        if foreshadow_recommendations:
            prompt += (
                "\n\n## 💡 【伏笔收回建议】\n"
                "基于当前章节情境，以下是历史上尚未揭示/收回的相似伏笔。"
                "强烈建议您在本章场景中，引导 AI 揭示或收回以下伏笔（至少推荐 1 个，并在场景的 must_include 中明确指出）：\n"
                f"{foreshadow_recommendations}"
            )
        if runtime_context:
            prompt += (
                "\n\n## 📐 【体量与规划约束】\n"
                "请严格遵守以下运行时策略（场景数量不得超过上限）：\n"
                f"{runtime_context}"
            )
        if quality_rewrite_hints and quality_rewrite_hints.strip():
            prompt += (
                "\n\n## 🛡️ 【质量门禁待修复】\n"
                "上一轮回滚审校未通过，请在场景 must_include / must_not_include 中体现下列修复要求：\n"
                f"{quality_rewrite_hints.strip()}"
            )
        if must_fix:
            issues_text = json.dumps(must_fix, ensure_ascii=False, indent=2)
            prompt += (
                "\n\n## 必须修复的问题（来自审计）\n"
                "以下问题在上一轮审计中被标记为情节/结构层面的问题，"
                "请在规划时将修复要求融入对应场景的 must_include 中：\n"
                f"{issues_text}"
            )
        if continuity_context and continuity_context.strip():
            prompt += (
                "\n\n## 跨章衔接与角色一致性（硬性约束）\n"
                f"{continuity_context.strip()}"
            )
        prompt += (
            "\n\n输出硬约束：只输出一个完整、可解析的 JSON 对象；不要 Markdown、"
            "解释或注释。每个字符串尽量使用短句，确保响应在一次输出内完整结束。"
        )
        return prompt.strip()

    @staticmethod
    def _build_parse_retry_prompt(
        prompt: str, error: LLMResponseError, max_plan_scenes: int
    ) -> str:
        """Make a compact second request after a malformed JSON response.

        Do not include the malformed model output: it can be very large and
        repeating it makes another truncation more likely.  The original
        prompt remains the source of truth for the chapter constraints.
        """
        error_summary = str(error).strip()[:240]
        return (
            f"{prompt}\n\n"
            "【JSON 格式重试】上一条章规划响应未形成完整 JSON，可能在输出上限处被截断。"
            f"解析错误摘要：{error_summary}\n"
            f"请重新生成完整结果：场景不超过 {max_plan_scenes} 个；每个字符串保持简短；"
            "只输出一个 JSON 对象，不要 Markdown、解释或省略结尾的引号/括号。"
        ).strip()

    def _parse_and_validate_plan(
        self,
        raw: str,
        chapter_id: str,
        chapter_goal: str,
        max_plan_scenes: int = 12,
        root_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        try:
            plan = loads_json_object(raw)
            # Validate scene cards
            scenes = plan.get("scenes", [])
            validated_scenes = []
            required_fields = {"scene_id"}
            for i, scene in enumerate(scenes):
                if not isinstance(scene, dict):
                    logger.warning("Scene %d is not a dict, skipping", i)
                    continue
                missing = required_fields - set(scene.keys())
                if missing:
                    logger.warning("Scene %d missing fields %s, adding defaults", i, missing)
                    for f in missing:
                        scene.setdefault(f, f"scene_{i + 1}")
                # Ensure purpose exists
                scene.setdefault("purpose", "")
                scene.setdefault("target_chars", [400, 800])
                scene_type = scene.get("scene_type") or self._infer_scene_type(scene.get("purpose", ""))
                if scene_type not in VALID_SCENE_TYPES:
                    scene_type = "setup"
                detail_level = scene.get("detail_level") or self._detail_for_scene(scene_type)
                if detail_level not in VALID_DETAIL_LEVELS:
                    detail_level = self._detail_for_scene(scene_type)
                scene["scene_type"] = scene_type
                scene["detail_level"] = detail_level
                scene["hook_type"] = scene.get("hook_type") or "info"
                must_not_include = scene.get("must_not_include", [])
                if not isinstance(must_not_include, list):
                    must_not_include = [str(must_not_include)]
                for rule in ANTI_AI_MUST_NOT_INCLUDE:
                    if rule not in must_not_include:
                        must_not_include.append(rule)
                scene["must_not_include"] = must_not_include
                validated_scenes.append(scene)
            if len(validated_scenes) > max_plan_scenes:
                logger.warning(
                    "Planner returned %d scenes, truncating to max_plan_scenes=%d",
                    len(validated_scenes),
                    max_plan_scenes,
                )
                validated_scenes = validated_scenes[:max_plan_scenes]
            plan["scenes"] = validated_scenes
            if root_dir is not None:
                from novel_agent.services.continuity_pack import enrich_plan_characters

                plan = enrich_plan_characters(plan, root_dir, chapter_id)
            return plan
        except Exception as exc:
            logger.error("Failed to parse planner output: %s", exc)
            raise LLMResponseError(f"章规划输出无法解析，已中止生成: {exc}") from exc

    def create_plan(
        self,
        chapter_id: str,
        chapter_goal: str,
        must_fix: Optional[List[Dict[str, Any]]] = None,
        duplicate_warnings: Optional[str] = None,
        foreshadow_recommendations: Optional[str] = None,
        runtime_context: Optional[str] = None,
        quality_rewrite_hints: Optional[str] = None,
        max_plan_scenes: int = 12,
        continuity_context: Optional[str] = None,
        root_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(
            chapter_id,
            chapter_goal,
            must_fix,
            duplicate_warnings,
            foreshadow_recommendations,
            runtime_context,
            quality_rewrite_hints,
            continuity_context,
        )
        raw = self.run(prompt)
        try:
            return self._parse_and_validate_plan(
                raw,
                chapter_id,
                chapter_goal,
                max_plan_scenes=max_plan_scenes,
                root_dir=root_dir,
            )
        except LLMResponseError as first_error:
            if _PLAN_PARSE_RETRIES <= 0:
                raise
            logger.warning(
                "Planner response was not parseable; retrying once: %s", first_error
            )
            retry_raw = self.run(
                self._build_parse_retry_prompt(prompt, first_error, max_plan_scenes)
            )
            try:
                return self._parse_and_validate_plan(
                    retry_raw,
                    chapter_id,
                    chapter_goal,
                    max_plan_scenes=max_plan_scenes,
                    root_dir=root_dir,
                )
            except LLMResponseError as retry_error:
                raise LLMResponseError(
                    f"{retry_error}（首次解析失败后自动重试仍失败）"
                ) from retry_error

    async def acreate_plan(
        self,
        chapter_id: str,
        chapter_goal: str,
        must_fix: Optional[List[Dict[str, Any]]] = None,
        duplicate_warnings: Optional[str] = None,
        foreshadow_recommendations: Optional[str] = None,
        runtime_context: Optional[str] = None,
        quality_rewrite_hints: Optional[str] = None,
        max_plan_scenes: int = 12,
        continuity_context: Optional[str] = None,
        root_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(
            chapter_id,
            chapter_goal,
            must_fix,
            duplicate_warnings,
            foreshadow_recommendations,
            runtime_context,
            quality_rewrite_hints,
            continuity_context,
        )
        raw = await self.arun(prompt)
        try:
            return self._parse_and_validate_plan(
                raw,
                chapter_id,
                chapter_goal,
                max_plan_scenes=max_plan_scenes,
                root_dir=root_dir,
            )
        except LLMResponseError as first_error:
            if _PLAN_PARSE_RETRIES <= 0:
                raise
            logger.warning(
                "Planner response was not parseable; retrying once: %s", first_error
            )
            retry_raw = await self.arun(
                self._build_parse_retry_prompt(prompt, first_error, max_plan_scenes)
            )
            try:
                return self._parse_and_validate_plan(
                    retry_raw,
                    chapter_id,
                    chapter_goal,
                    max_plan_scenes=max_plan_scenes,
                    root_dir=root_dir,
                )
            except LLMResponseError as retry_error:
                raise LLMResponseError(
                    f"{retry_error}（首次解析失败后自动重试仍失败）"
                ) from retry_error

    def _infer_scene_type(self, purpose: str) -> str:
        if any(word in purpose for word in ("爆发", "高潮", "兑现", "反击", "冲突")):
            return "burst"
        if any(word in purpose for word in ("蓄力", "压迫", "逼近", "试探")):
            return "build"
        if any(word in purpose for word in ("过渡", "转场", "时间推进")):
            return "transition"
        return "setup"

    def _detail_for_scene(self, scene_type: str) -> str:
        return {
            "setup": "brief",
            "build": "normal",
            "burst": "full",
            "transition": "skip",
        }.get(scene_type, "brief")
