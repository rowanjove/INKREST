"""Managing Editor Agent — splits macro outline into chapter queue."""

import json
from typing import Any, Dict, List, Optional

from novel_agent.agents.base import PromptAgent
from novel_agent.control.chapter_window import normalize_chapter_window
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.managing_editor")


class ManagingEditorAgent(PromptAgent):
    """Splits the Chief Editor's outline into an actionable chapter queue."""

    def __init__(self, llm, prompts=None):
        super().__init__("managing_editor", llm)
        self.prompts = prompts

    def _build_prompt(
        self,
        outline: Dict[str, Any],
        arc_index: int = 0,
        *,
        writing_context: str = "",
    ) -> tuple:
        """Build prompt for split_chapters and extract arc.
        
        Returns:
            Tuple of (prompt, arc)
        """
        template = self.prompts.load("managing_editor") if self.prompts else ""
        arcs = outline.get("macro_outline", [])
        if arc_index >= len(arcs):
            arc_index = 0
        arc = arcs[arc_index] if arcs else {}
        context = {
            "protagonist": outline.get("protagonist", {}),
            "main_cast": outline.get("main_cast", []),
            "antagonistic_forces": outline.get("antagonistic_forces", []),
            "forbidden_moves": outline.get("forbidden_moves", []),
            "macro_outline": arc,
            "core_theme": outline.get("core_theme", ""),
            "genre_genes": outline.get("genre_genes", {}),
            "logline": outline.get("logline", ""),
        }
        input_json = json.dumps(context, ensure_ascii=False, indent=2)
        parts = [template, f"\n\n## 输入\n{input_json}"]
        if writing_context.strip():
            parts.append(f"\n\n{writing_context.strip()}")
        prompt = "".join(parts).strip()
        return prompt, arc

    def _parse_and_validate_arc(self, raw: str, arc: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = loads_json_object(raw)
            result = self._validate_arc(result, arc)
            return result
        except Exception as exc:
            logger.error("Failed to parse managing editor output: %s", exc)
            return self._fallback_arc(arc)

    def split_chapters(
        self,
        outline: Dict[str, Any],
        arc_index: int = 0,
        *,
        writing_context: str = "",
    ) -> Dict[str, Any]:
        """Split a macro outline arc into a chapter queue."""
        prompt, arc = self._build_prompt(outline, arc_index, writing_context=writing_context)
        raw = self.run(prompt)
        return self._parse_and_validate_arc(raw, arc)

    async def asplit_chapters(
        self,
        outline: Dict[str, Any],
        arc_index: int = 0,
        *,
        writing_context: str = "",
    ) -> Dict[str, Any]:
        """Split a macro outline arc into a chapter queue asynchronously."""
        prompt, arc = self._build_prompt(outline, arc_index, writing_context=writing_context)
        raw = await self.arun(prompt)
        return self._parse_and_validate_arc(raw, arc)

    def split_all_arcs(self, outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split all arcs in the outline into chapter queues."""
        arcs = outline.get("macro_outline", [])
        results = []
        for i in range(len(arcs)):
            arc_result = self.split_chapters(outline, arc_index=i)
            results.append(arc_result)
        return results

    async def asplit_all_arcs(self, outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split all arcs in the outline into chapter queues asynchronously."""
        arcs = outline.get("macro_outline", [])
        results = []
        for i in range(len(arcs)):
            arc_result = await self.asplit_chapters(outline, arc_index=i)
            results.append(arc_result)
        return results

    def _validate_arc(
        self, result: Dict[str, Any], arc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate chapter queue and fix common issues."""
        result.setdefault("arc_id", arc.get("arc_id", "A01"))
        result.setdefault("arc_name", arc.get("name", "第一阶段"))
        result.setdefault("arc_goal", arc.get("goal", ""))

        chapters = result.get("chapters", [])
        validated = []
        for i, ch in enumerate(chapters):
            if not isinstance(ch, dict):
                logger.warning("Chapter %d is not a dict, skipping", i)
                continue
            ch.setdefault("chapter_id", f"{i + 1:03d}")
            ch.setdefault("chapter_title", f"第 {i + 1} 章")
            ch.setdefault("chapter_goal", "待定")
            ch.setdefault("input_state", "")
            ch.setdefault("output_state", "")
            ch.setdefault("reader_payoff", "")
            ch.setdefault("hook", "")
            ch.setdefault("must_include", [])
            ch.setdefault("must_not_include", [])
            validated.append(ch)

        # Verify state chain: output_state[i] should match input_state[i+1]
        for i in range(len(validated) - 1):
            curr_out = validated[i].get("output_state", "")
            next_in = validated[i + 1].get("input_state", "")
            if curr_out and next_in and curr_out != next_in:
                logger.info(
                    "State chain mismatch between chapter %s and %s: '%s' vs '%s'",
                    validated[i]["chapter_id"],
                    validated[i + 1]["chapter_id"],
                    curr_out[:50],
                    next_in[:50],
                )

        result["chapters"] = normalize_chapter_window(validated)
        return result

    def _fallback_arc(self, arc: Dict[str, Any]) -> Dict[str, Any]:
        """Return a minimal valid arc when LLM fails."""
        chapters_range = arc.get("chapters", "1-5")
        try:
            start, end = chapters_range.split("-")
            start_num, end_num = int(start.strip()), int(end.strip())
        except (ValueError, AttributeError):
            start_num, end_num = 1, 5

        chapters = []
        for i in range(start_num, end_num + 1):
            chapters.append({
                "chapter_id": f"{i:03d}",
                "chapter_title": f"第 {i} 章",
                "chapter_goal": arc.get("goal", "推进剧情"),
                "input_state": "",
                "output_state": "",
                "reader_payoff": "",
                "hook": "",
                "must_include": [],
                "must_not_include": [],
            })

        return {
            "arc_id": arc.get("arc_id", "A01"),
            "arc_name": arc.get("name", "第一阶段"),
            "arc_goal": arc.get("goal", ""),
            "chapters": normalize_chapter_window(chapters),
        }
