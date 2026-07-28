import json

from novel_agent.agents.base import PromptAgent
from novel_agent.logging_config import get_logger
from novel_agent.scripts.count_chars import wordcount_report

logger = get_logger("agents.length_fix")


class LengthFixAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("length_fix", llm)
        self.prompts = prompts

    def _build_prompt_and_role(self, text: str, target_range) -> tuple:
        """Calculate wordcount report and build instructions, prompt and determine agent role.
        
        Returns:
            Tuple of (prompt, role, should_skip, text_if_skipped)
        """
        report = wordcount_report(text, target_range[0], target_range[1])
        if report["status"] == "ok":
            return "", "", True, text
        if report["status"] == "under":
            role = "expander"
            template_name = "expander"
            instructions = (
                f"【硬性字数控制指令】\n"
                f"当前正文字数仅为 {report['count']} 字，远低于目标字数区间下限 {report['target_min']} 字！\n"
                f"目前字数缺口高达 {report['missing']} 字！\n"
                f"请你必须通过强力补充环境压力、动作细节链、感官体验、内心潜台词和微表情，"
                f"大幅度拉长整体文段长度。请确保修改后的总字数绝对不得低于 {report['target_min']} 字，且完全维持剧情脉络不变！"
            )
        else:
            role = "compressor"
            template_name = "compressor"
            instructions = (
                f"【硬性字数控制指令】\n"
                f"当前正文字数已达 {report['count']} 字，超出了目标区间上限 {report['target_max']} 字！\n"
                f"目前字数超出了 {report['excess']} 字，请剔除冗余段落或重复描写，确保字数收窄到上限以内。"
            )
        template = self.prompts.load(template_name) if self.prompts else ""
        prompt = (
            f"{template}\n\n"
            f"请根据字数报告修正文段，保持剧情不变。\n"
            f"字数报告：{json.dumps(report, ensure_ascii=False)}\n\n"
            f"{instructions}\n\n"
            f"以下是待修正文本：\n{text}"
        ).strip()
        return prompt, role, False, ""

    def adjust(self, text: str, target_range) -> str:
        prompt, role, should_skip, text_if_skipped = self._build_prompt_and_role(text, target_range)
        if should_skip:
            return text_if_skipped
        return self.llm.generate(role, prompt).strip()

    async def aadjust(self, text: str, target_range) -> str:
        prompt, role, should_skip, text_if_skipped = self._build_prompt_and_role(text, target_range)
        if should_skip:
            return text_if_skipped
        if hasattr(self.llm, "agenerate"):
            res = await self.llm.agenerate(role, prompt)
        else:
            res = self.llm.generate(role, prompt)
        return res.strip()
