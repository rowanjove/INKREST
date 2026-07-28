import json

from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.continuity_checker")


class ContinuityCheckerAgent(PromptAgent):
    """Checks chapter text against asset library for continuity violations."""

    def __init__(self, llm, prompts=None):
        super().__init__("continuity_checker", llm)
        self.prompts = prompts

    def _build_prompt(self, chapter_text: str, state_text: str = "") -> str:
        template = self.prompts.load("continuity_checker") if self.prompts else ""
        return (
            f"{template}\n\n"
            "## 当前状态\n"
            f"{state_text or '暂无。'}\n\n"
            "## 章节正文\n"
            f"{chapter_text}"
        ).strip()

    def _parse_and_validate_check(self, raw: str) -> dict:
        try:
            return loads_json_object(raw)
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Failed to parse continuity checker output: %s", exc)
            return {
                "pass": False,
                "issues": [{"type": "parse_error", "severity": "low", "text": "", "why": f"Agent 输出无法解析为 JSON: {exc}", "fix": "重新运行"}],
                "error": True,
                "error_detail": str(exc),
            }

    def check(self, chapter_text: str, state_text: str = "") -> dict:
        prompt = self._build_prompt(chapter_text, state_text)
        raw = self.run(prompt)
        return self._parse_and_validate_check(raw)

    async def acheck(self, chapter_text: str, state_text: str = "") -> dict:
        prompt = self._build_prompt(chapter_text, state_text)
        raw = await self.arun(prompt)
        return self._parse_and_validate_check(raw)
