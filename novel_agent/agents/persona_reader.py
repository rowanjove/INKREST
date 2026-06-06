"""Persona Reader Agent — simulates real readers to evaluate novel chapters.

Supports three different reader preferences:
1. fan: 小白爽文读者
2. critic: 挑剔的老书虫
3. romance: 甜宠/情感倾向读者
"""

import json
from typing import Any, Dict, Optional
from pathlib import Path

from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.persona_reader")


class PersonaReaderAgent(PromptAgent):
    """Simulates a reader profile to review novel chapters and output feedback."""

    def __init__(self, llm, prompts=None, root_dir: Optional[Path] = None):
        super().__init__("persona_reader", llm)
        self.prompts = prompts
        self.root_dir = Path(root_dir) if root_dir else Path(".")

    def _load_persona_prompt(self, persona_type: str) -> str:
        """Load the specific prompt template for the reader persona."""
        # 1. 尝试从 prompt 库中动态加载
        prompt_tmpl = ""
        if self.prompts:
            try:
                prompt_tmpl = self.prompts.load(f"reader_persona_{persona_type}")
            except Exception:
                pass
        
        # 2. 如果没加载到，直接从 prompts 目录下的 Markdown 文件加载
        if not prompt_tmpl:
            file_path = self.root_dir / "prompts" / f"reader_persona_{persona_type}.md"
            if file_path.exists():
                try:
                    prompt_tmpl = file_path.read_text(encoding="utf-8").strip()
                except Exception as exc:
                    logger.warning("Failed to load prompt file %s: %s", file_path, exc)
                    
        # 3. 兜底默认模板
        if not prompt_tmpl:
            prompt_tmpl = f"你是一个偏好为 {persona_type} 的网文读者。请评估本章并输出 json。"
            
        return prompt_tmpl

    def _build_prompt(self, chapter_text: str, chapter_id: str, persona_type: str) -> str:
        persona_tmpl = self._load_persona_prompt(persona_type)
        return f"{persona_tmpl}\n\n## 待评测章节正文 (CH {chapter_id})\n{chapter_text}"

    def _parse_and_validate(self, raw: str, persona_type: str) -> Dict[str, Any]:
        try:
            result = loads_json_object(raw)
            result.setdefault("persona_name", persona_type)
            result.setdefault("score", 7.0)
            result.setdefault("danmaku", [])
            result.setdefault("highlights", [])
            result.setdefault("dislikes", [])
            result.setdefault("summary", "")
            return result
        except Exception as exc:
            logger.error("Failed to parse reader persona evaluation for %s: %s", persona_type, exc)
            return self._empty_evaluation(persona_type)

    def evaluate(self, chapter_text: str, chapter_id: str, persona_type: str) -> Dict[str, Any]:
        """Synchronously evaluate a chapter text."""
        if not chapter_text or not chapter_text.strip():
            return self._empty_evaluation(persona_type)
        prompt = self._build_prompt(chapter_text, chapter_id, persona_type)
        raw = self.run(prompt)
        return self._parse_and_validate(raw, persona_type)

    async def aevaluate(self, chapter_text: str, chapter_id: str, persona_type: str) -> Dict[str, Any]:
        """Asynchronously evaluate a chapter text."""
        if not chapter_text or not chapter_text.strip():
            return self._empty_evaluation(persona_type)
        prompt = self._build_prompt(chapter_text, chapter_id, persona_type)
        raw = await self.arun(prompt)
        return self._parse_and_validate(raw, persona_type)

    @staticmethod
    def _empty_evaluation(persona_type: str) -> Dict[str, Any]:
        name_map = {"fan": "爽文热衷党", "critic": "深度逻辑党", "romance": "甜宠情感党"}
        return {
            "persona_name": name_map.get(persona_type, persona_type),
            "score": 5.0,
            "danmaku": ["没看懂...", "感觉这章稍微有点平淡。"],
            "highlights": ["暂无亮点分析"],
            "dislikes": ["系统解析评价异常"],
            "summary": "大模型评测失败，生成了默认评估。"
        }
