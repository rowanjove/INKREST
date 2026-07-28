from novel_agent.agents.base import PromptAgent
from novel_agent.logging_config import get_logger

logger = get_logger("agents.chapter_summary")


class ChapterSummaryAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("chapter_summary", llm)
        self.prompts = prompts

    def _build_prompt(self, chapter_text: str) -> str:
        template = self.prompts.load("chapter_summary") if self.prompts else ""
        return (
            f"{template}\n\n"
            "请根据以下章节正文生成 Markdown 章节总结，必须包含章节概述、人物发展、看点/爽点、故事伏笔、收尾特征、张力心电图、总体评分。\n\n"
            f"{chapter_text}"
        ).strip()

    def summarize(self, chapter_text: str) -> str:
        prompt = self._build_prompt(chapter_text)
        return self.run(prompt).strip()

    async def asummarize(self, chapter_text: str) -> str:
        prompt = self._build_prompt(chapter_text)
        res = await self.arun(prompt)
        return res.strip()
