"""Intent Router and Model Router for ShanShan Assistant.

Provides:
1. IntentRouter: Identifies user intent from natural language instructions when no slash command is used.
2. ModelRouter: Routes requests to the appropriate model tier (creative, reasoning, economy, assistant) based on skill policy.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from novel_agent.assistant.models import ActiveEditorContext


class IntentRouter:
    # Keyword patterns mapped to skill IDs
    PATTERNS: List[tuple[re.Pattern, str]] = [
        (re.compile(r"(?:润色|修饰|文笔|降ai味|改写一下|优化语句)", re.IGNORECASE), "polish"),
        (re.compile(r"(?:续写|接下去写|继续写|往下写|写下一段)", re.IGNORECASE), "continue"),
        (re.compile(r"(?:扩写|丰富细节|充实内容|展开写|细化描写)", re.IGNORECASE), "expand"),
        (re.compile(r"(?:压缩|精简|删掉废话|缩短|缩写)", re.IGNORECASE), "compress"),
        (re.compile(r"(?:对白|台词|重写对话|说话风格|对话改写)", re.IGNORECASE), "dialogue"),
        (re.compile(r"(?:人物口吻|口吻|语气|不像他说的|角色口吻|不像她说的)", re.IGNORECASE), "character_voice"),
        (re.compile(r"(?:查冲突|连续性|吃书|前后矛盾|逻辑漏洞|自相矛盾|设定冲突)", re.IGNORECASE), "conflict_check"),
        (re.compile(r"(?:查设定|人物卡|人设|世界规则|能力设定|角色设定|背景设定|背景资料|设定)", re.IGNORECASE), "query_setting"),


        (re.compile(r"(?:审章|审阅本章|检查本章|这一章怎么样|整章评估)", re.IGNORECASE), "review_chapter"),
        (re.compile(r"(?:伏笔|暗线|伏笔检查|加强伏笔|伏笔账本)", re.IGNORECASE), "foreshadowing"),
        (re.compile(r"(?:策划|脑暴|情节推演|剧情走向|剧情构思|点子)", re.IGNORECASE), "brainstorm"),
        (re.compile(r"(?:拆场|分场|场景划分|scene)", re.IGNORECASE), "scene_breakdown"),
        (re.compile(r"(?:章纲|细纲|分章大纲|章节目标)", re.IGNORECASE), "chapter_outline"),
        (re.compile(r"(?:总结|摘要|本章概括|剧情提要)", re.IGNORECASE), "summary"),
        (re.compile(r"(?:诊断|排障|失败原因|报错|流水线.*(?:暂停|报错|失败)|(?:为什么|怎么).*(?:暂停|报错|失败))", re.IGNORECASE), "diagnose"),
    ]

    @classmethod
    def detect_skill(
        cls,
        message: str,
        editor_context: Optional[ActiveEditorContext] = None,
    ) -> Optional[str]:
        """Infers the most appropriate skill ID based on natural language keywords and context."""
        text = message.strip()
        if not text:
            return None

        for pattern, skill_id in cls.PATTERNS:
            if pattern.search(text):
                return skill_id

        # Fallback heuristic based on selection context:
        # If user selected text and asks a short command like "帮我改改"
        if editor_context and editor_context.selected_text:
            if any(k in text for k in ("改", "修", "变好", "处理")):
                return "polish"

        return None


class ModelRouter:
    """Selects the target model based on Skill's model_policy and pipeline configuration."""

    POLICY_MAPPINGS = {
        "creative": ["writer_model_id", "creative_model_id", "daily_model_id"],
        "reasoning": ["reasoning_model_id", "logic_model_id", "daily_model_id"],
        "economy": ["economy_model_id", "fast_model_id", "assistant_model_id", "daily_model_id"],
        "balanced": ["daily_model_id", "default_model_id"],
    }

    @classmethod
    def resolve_model_id(
        cls,
        model_policy: Optional[str] = None,
        root_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Resolves the best concrete model ID for a given model policy."""
        try:
            from novel_agent.pipeline import load_pipeline_settings
            if not root_dir or not Path(root_dir).is_dir():
                return None
            settings = load_pipeline_settings(Path(root_dir))
            llm_settings = settings.get("llm", {})

            policy = (model_policy or "balanced").lower()
            candidate_keys = cls.POLICY_MAPPINGS.get(policy, ["daily_model_id", "default_model_id"])

            for key in candidate_keys:
                val = llm_settings.get(key)
                if val and isinstance(val, str) and val.strip():
                    return val.strip()

            # Fallback to assistant model or daily model
            assistant_cfg = llm_settings.get("assistant")
            if isinstance(assistant_cfg, dict) and assistant_cfg.get("model_ref"):
                return assistant_cfg["model_ref"]

            return llm_settings.get("daily_model_id") or llm_settings.get("default_model_id")
        except Exception:
            return None
