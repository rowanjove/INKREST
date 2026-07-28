from typing import List, Tuple
from novel_agent.agents.base import PromptAgent
from novel_agent.logging_config import get_logger

logger = get_logger("agents.stitch_editor")


class StitchEditorAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("stitch_editor", llm)
        self.prompts = prompts

    def _build_prompt(self, chapter_text: str) -> str:
        template = self.prompts.load("stitch_editor") if self.prompts else ""
        return (
            f"{template}\n\n"
            "请修复多场景拼接后的接缝，不能改变剧情，输出完整章节正文。\n\n"
            + chapter_text
        ).strip()

    def _build_boundary_prompt(self, boundary_text: str) -> str:
        template = self.prompts.load("stitch_editor") if self.prompts else ""
        return (
            f"{template}\n\n"
            "请修复场景A与场景B拼接处的过渡缝合，使叙事、时间与空间过渡顺畅自然，消除生硬的拼凑感。\n"
            "只输出缝合过渡后的文本（包含场景A结尾与场景B开头），保持主线情节、人物动作完全一致，不要任何解释说明。\n\n"
            + boundary_text
        ).strip()

    def edit(self, chapter_text: str) -> str:
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty input to stitch editor, returning empty string")
            return ""
        prompt = self._build_prompt(chapter_text)
        return self.run(prompt).strip()

    async def aedit(self, chapter_text: str) -> str:
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty input to stitch editor, returning empty string")
            return ""
        prompt = self._build_prompt(chapter_text)
        res = await self.arun(prompt)
        return res.strip()

    def edit_boundary(self, boundary_text: str) -> str:
        prompt = self._build_boundary_prompt(boundary_text)
        return self.run(prompt).strip()

    async def aedit_boundary(self, boundary_text: str) -> str:
        prompt = self._build_boundary_prompt(boundary_text)
        res = await self.arun(prompt)
        return res.strip()

    def edit_scenes(self, scenes: List[str]) -> str:
        if not scenes:
            return ""
        current_text = scenes[0]
        for next_scene in scenes[1:]:
            if not next_scene.strip():
                continue
            prefix, tail = self._split_tail(current_text)
            head, suffix = self._split_head(next_scene)
            
            if not tail.strip() or not head.strip():
                current_text = "\n\n".join(p for p in [current_text, next_scene] if p)
                continue
                
            boundary_prompt = (
                f"=== 场景A结尾 ===\n{tail}\n\n"
                f"=== 场景B开头 ===\n{head}"
            )
            stitched_boundary = self.edit_boundary(boundary_prompt)
            current_text = "\n\n".join(p for p in [prefix, stitched_boundary, suffix] if p)
        return current_text

    async def aedit_scenes(self, scenes: List[str]) -> str:
        if not scenes:
            return ""
        current_text = scenes[0]
        for next_scene in scenes[1:]:
            if not next_scene.strip():
                continue
            prefix, tail = self._split_tail(current_text)
            head, suffix = self._split_head(next_scene)
            
            if not tail.strip() or not head.strip():
                current_text = "\n\n".join(p for p in [current_text, next_scene] if p)
                continue
                
            boundary_prompt = (
                f"=== 场景A结尾 ===\n{tail}\n\n"
                f"=== 场景B开头 ===\n{head}"
            )
            stitched_boundary = await self.aedit_boundary(boundary_prompt)
            current_text = "\n\n".join(p for p in [prefix, stitched_boundary, suffix] if p)
        return current_text

    def _split_tail(self, text: str, target_chars: int = 500, max_paragraphs: int = 3) -> Tuple[str, str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return "", ""
        tail_paras = []
        char_count = 0
        while paragraphs and len(tail_paras) < max_paragraphs and char_count < target_chars:
            p = paragraphs.pop()
            tail_paras.insert(0, p)
            char_count += len(p)
        prefix = "\n\n".join(paragraphs)
        tail = "\n\n".join(tail_paras)
        return prefix, tail

    def _split_head(self, text: str, target_chars: int = 500, max_paragraphs: int = 3) -> Tuple[str, str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return "", ""
        head_paras = []
        char_count = 0
        while paragraphs and len(head_paras) < max_paragraphs and char_count < target_chars:
            p = paragraphs.pop(0)
            head_paras.append(p)
            char_count += len(p)
        head = "\n\n".join(head_paras)
        suffix = "\n\n".join(paragraphs)
        return head, suffix

