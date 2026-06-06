import asyncio
from typing import List, Optional
from novel_agent.agents.base import PromptAgent
from novel_agent.logging_config import get_logger

logger = get_logger("agents.style_editor")


class StyleEditorAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("style_editor", llm)
        self.prompts = prompts
        self.max_chunk_chars = 1200  # 默认 1200 字拆分 Chunk

    def _build_prompt(self, chapter_text: str) -> str:
        template = self.prompts.load("style_editor") if self.prompts else ""
        return (
            f"{template}\n\n"
            "请降低文本中的模板感、空泛感和 AI 腔，不新增剧情，输出完整修订版。\n\n"
            + chapter_text
        ).strip()

    def _build_chunk_prompt(self, chunk: str, prev_chunk: Optional[str] = None, next_chunk: Optional[str] = None) -> str:
        template = self.prompts.load("style_editor") if self.prompts else ""
        
        context_str = ""
        if prev_chunk and prev_chunk.strip():
            context_str += f"=== 前文参考（不要输出前文，仅用于衔接） ===\n{prev_chunk}\n\n"
        
        context_str += f"=== 待润色片段 ===\n{chunk}\n\n"
        
        if next_chunk and next_chunk.strip():
            context_str += f"=== 后文参考（不要输出后文，仅用于衔接） ===\n{next_chunk}\n\n"
            
        return (
            f"{template}\n\n"
            "请对【待润色片段】进行文风润色，降低模板感和 AI 腔，保持情节、人物动作完全一致，不要任何解释说明。\n"
            "【特别提示】：\n"
            "1. 绝对不要输出《前文参考》或《后文参考》中的任何段落，仅输出《待润色片段》润色后的文本。\n"
            "2. 不要把正文压缩成梗概，保持段落数量和细节逻辑大致相当。\n"
            "3. 只输出润色后的正文，不要输出任何其他的字句或 Markdown 标识符。\n\n"
            f"{context_str}"
        ).strip()

    def _split_into_chunks(self, text: str, max_chunk_chars: int) -> List[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_len = 0
        for p in paragraphs:
            if current_len + len(p) > max_chunk_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_len = len(p)
            else:
                current_chunk.append(p)
                current_len += len(p) + 2  # account for \n\n
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return chunks

    def _get_tail_paras(self, text: str, max_paras: int = 2) -> str:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return ""
        return "\n\n".join(paragraphs[-max_paras:])

    def _get_head_paras(self, text: str, max_paras: int = 2) -> str:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return ""
        return "\n\n".join(paragraphs[:max_paras])

    def edit(self, chapter_text: str) -> str:
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty input to style editor, returning empty string")
            return ""
        
        # 字数较少时直发，避免不必要的切分和上下文开销
        if len(chapter_text) <= self.max_chunk_chars:
            prompt = self._build_prompt(chapter_text)
            return self.run(prompt).strip()

        logger.info("Chapter length (%d) exceeds max_chunk_chars (%d), enabling sliding window style editing.", 
                    len(chapter_text), self.max_chunk_chars)
        chunks = self._split_into_chunks(chapter_text, self.max_chunk_chars)
        polished_chunks = []
        
        for idx, chunk in enumerate(chunks):
            prev_chunk = chunks[idx - 1] if idx > 0 else None
            next_chunk = chunks[idx + 1] if idx < len(chunks) - 1 else None
            
            prev_context = self._get_tail_paras(prev_chunk) if prev_chunk else None
            next_context = self._get_head_paras(next_chunk) if next_chunk else None
            
            prompt = self._build_chunk_prompt(chunk, prev_context, next_context)
            logger.debug("Polishing style editor chunk %d/%d (len=%d)", idx + 1, len(chunks), len(chunk))
            polished = self.run(prompt).strip()
            if polished:
                polished_chunks.append(polished)
            else:
                logger.warning("Polished chunk %d was empty, falling back to original chunk", idx + 1)
                polished_chunks.append(chunk)
                
        return "\n\n".join(polished_chunks)

    async def aedit(self, chapter_text: str) -> str:
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty input to style editor, returning empty string")
            return ""

        if len(chapter_text) <= self.max_chunk_chars:
            prompt = self._build_prompt(chapter_text)
            res = await self.arun(prompt)
            return res.strip()

        logger.info("Chapter length (%d) exceeds max_chunk_chars (%d), enabling sliding window style editing (Async).", 
                    len(chapter_text), self.max_chunk_chars)
        chunks = self._split_into_chunks(chapter_text, self.max_chunk_chars)
        
        async def _polish_chunk(idx: int, chunk: str) -> str:
            prev_chunk = chunks[idx - 1] if idx > 0 else None
            next_chunk = chunks[idx + 1] if idx < len(chunks) - 1 else None
            
            prev_context = self._get_tail_paras(prev_chunk) if prev_chunk else None
            next_context = self._get_head_paras(next_chunk) if next_chunk else None
            
            prompt = self._build_chunk_prompt(chunk, prev_context, next_context)
            logger.debug("Polishing style editor chunk %d/%d (len=%d, Async)", idx + 1, len(chunks), len(chunk))
            
            try:
                polished = await self.arun(prompt)
                polished = polished.strip()
                if polished:
                    return polished
            except Exception as exc:
                logger.error("Failed to polish style editor chunk %d asynchronously: %s", idx + 1, exc)
                
            return chunk

        tasks = [_polish_chunk(idx, chunk) for idx, chunk in enumerate(chunks)]
        polished_chunks = await asyncio.gather(*tasks)
        return "\n\n".join(polished_chunks)
