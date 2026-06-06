"""Chief Editor Agent — generates macro-level novel outline from theme/genre."""

import json
from typing import Any, Dict, List, Optional

from novel_agent.agents.base import PromptAgent
from novel_agent.control.genre_genes import ensure_genre_genes
from novel_agent.control.outline_structure import normalize_macro_outline
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.chief_editor")

# Required top-level fields in the outline
_REQUIRED_FIELDS = {"protagonist", "macro_outline"}
_STAGED_MIN_TARGET = 200
_STAGED_SCALES = frozenset({"long", "epic", "infinite"})


class ChiefEditorAgent(PromptAgent):
    """Generates the macro outline for an entire novel."""

    def __init__(self, llm, prompts=None):
        super().__init__("chief_editor", llm)
        self.prompts = prompts

    def _build_prompt(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
        scale_context: str = "",
    ) -> str:
        template = self.prompts.load("chief_editor") if self.prompts else ""
        input_block = json.dumps(
            {
                "theme": theme,
                "genre": genre,
                "target_length": f"约 {target_chapters} 章",
                "special_requirements": special_requirements or "无",
            },
            ensure_ascii=False,
            indent=2,
        )
        parts = [template, f"\n\n## 输入\n{input_block}"]
        if scale_context:
            parts.append(f"\n\n{scale_context}")
        return "".join(parts).strip()

    def _parse_and_validate_outline(
        self,
        raw: str,
        theme: str,
        genre: str,
        target_chapters: int,
    ) -> Dict[str, Any]:
        try:
            outline = loads_json_object(raw)
            outline = self._validate_outline(outline, theme, genre, target_chapters)
            return outline
        except Exception as exc:
            logger.error("Failed to parse chief editor output: %s", exc)
            return self._fallback_outline(theme, genre, target_chapters)

    def _should_stage_outline(self, target_chapters: int, scale_context: str) -> bool:
        if target_chapters >= _STAGED_MIN_TARGET:
            return True
        ctx = (scale_context or "").lower()
        return any(s in ctx for s in ("epic", "infinite", "超长篇", "500", "长篇"))

    def _plan_staged(
        self,
        theme: str,
        genre: str,
        target_chapters: int,
        special_requirements: str,
        scale_context: str,
    ) -> Dict[str, Any]:
        """Two-phase: skeleton macro arcs, then enrich turning_point/payoff in batches."""
        base = self._build_prompt(
            theme, genre, target_chapters, special_requirements, scale_context
        )
        step1 = (
            f"{base}\n\n【分段生成·第1步】先输出完整 L0 设定与 macro_outline 卷级骨架。"
            "每卷必须有 arc_id、name、chapters 跨度、goal（可简短）；"
            "turning_point、payoff 可暂写「待定」。不要逐章清单。"
        )
        raw1 = self.run(step1)
        outline = self._parse_and_validate_outline(raw1, theme, genre, target_chapters)
        macro = outline.get("macro_outline") or []
        if len(macro) <= 1:
            return outline

        batch_size = 4
        for offset in range(0, len(macro), batch_size):
            batch = macro[offset : offset + batch_size]
            enrich_input = json.dumps(
                {
                    "theme": theme,
                    "genre": genre,
                    "protagonist": outline.get("protagonist"),
                    "genre_genes": outline.get("genre_genes"),
                    "arcs_to_enrich": batch,
                },
                ensure_ascii=False,
                indent=2,
            )
            step2 = (
                f"{base}\n\n【分段生成·第2步】仅润色下列卷的 turning_point 与 payoff，"
                "保持 arc_id、name、chapters、goal 不变。只输出 JSON："
                '{"macro_outline":[...]}' f"\n\n## 输入\n{enrich_input}"
            )
            try:
                raw2 = self.run(step2)
                patch = loads_json_object(raw2)
                patched = patch.get("macro_outline") if isinstance(patch, dict) else None
                if isinstance(patched, list) and patched:
                    by_id = {str(a.get("arc_id")): a for a in patched if isinstance(a, dict)}
                    for i, arc in enumerate(macro):
                        aid = str(arc.get("arc_id") or "")
                        if aid in by_id:
                            macro[i] = {**arc, **by_id[aid]}
            except Exception as exc:
                logger.warning("Staged arc enrich batch %s failed: %s", offset, exc)
        outline["macro_outline"] = macro
        return self._validate_outline(outline, theme, genre, target_chapters)

    def plan_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
        scale_context: str = "",
    ) -> Dict[str, Any]:
        """Generate a macro outline for the novel."""
        if self._should_stage_outline(target_chapters, scale_context):
            return self._plan_staged(
                theme, genre, target_chapters, special_requirements, scale_context
            )
        prompt = self._build_prompt(
            theme, genre, target_chapters, special_requirements, scale_context
        )
        raw = self.run(prompt)
        return self._parse_and_validate_outline(raw, theme, genre, target_chapters)

    async def aplan_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
        scale_context: str = "",
    ) -> Dict[str, Any]:
        """Generate a macro outline for the novel asynchronously."""
        if self._should_stage_outline(target_chapters, scale_context):
            return self._plan_staged(
                theme, genre, target_chapters, special_requirements, scale_context
            )
        prompt = self._build_prompt(
            theme, genre, target_chapters, special_requirements, scale_context
        )
        raw = await self.arun(prompt)
        return self._parse_and_validate_outline(raw, theme, genre, target_chapters)

    def _validate_outline(
        self, outline: Dict[str, Any], theme: str, genre: str, target_chapters: int
    ) -> Dict[str, Any]:
        """Validate and fill defaults for the outline."""
        missing = _REQUIRED_FIELDS - set(outline.keys())
        if missing:
            logger.warning("Outline missing fields: %s, adding defaults", missing)

        # Ensure protagonist exists
        outline.setdefault("protagonist", {
            "name": "林越",
            "desire": "未设定",
            "flaw": "未设定",
            "edge": "未设定",
            "limit": "未设定",
        })

        # Ensure macro_outline exists with at least one arc
        if not outline.get("macro_outline"):
            outline["macro_outline"] = [{
                "arc_id": "A01",
                "name": "第一阶段",
                "chapters": f"1-{target_chapters}",
                "goal": theme,
                "turning_point": "待定",
                "payoff": "待定",
            }]

        # Fill other defaults
        outline.setdefault("title_options", [f"《{theme}》"])
        outline.setdefault("logline", theme)
        outline.setdefault("core_theme", theme)
        outline.setdefault("genre_positioning", genre)
        outline.setdefault("target_reader", "网文读者")
        outline.setdefault("reader_promise", ["精彩的故事"])
        outline.setdefault("world_rules", ["待定"])
        outline.setdefault("main_cast", [])
        outline.setdefault("antagonistic_forces", ["未知势力"])
        outline.setdefault("forbidden_moves", [])

        scale = ""
        sp = outline.get("scale_profile")
        if isinstance(sp, dict):
            scale = str(sp.get("scale") or "")
        outline["macro_outline"] = normalize_macro_outline(
            outline.get("macro_outline") or [],
            target_chapters=int(target_chapters or 20),
            scale=scale,
        )

        return ensure_genre_genes(outline)

    def _fallback_outline(
        self, theme: str, genre: str, target_chapters: int
    ) -> Dict[str, Any]:
        """Return a minimal valid outline when LLM fails."""
        logger.warning("Using fallback outline for theme: %s", theme)
        outline = {
            "title_options": [f"《{theme}》"],
            "logline": theme,
            "core_theme": theme,
            "genre_positioning": genre,
            "target_reader": "网文读者",
            "reader_promise": ["一个关于" + theme + "的故事"],
            "world_rules": ["待定"],
            "protagonist": {
                "name": "林越",
                "desire": "探索真相",
                "flaw": "过于执着",
                "edge": "特殊能力",
                "limit": "能力有代价",
            },
            "main_cast": [],
            "antagonistic_forces": ["未知势力"],
            "macro_outline": [{
                "arc_id": "A01",
                "name": "起始篇",
                "chapters": f"1-{target_chapters}",
                "goal": theme,
                "turning_point": "关键发现",
                "payoff": "初步揭开真相",
            }],
            "forbidden_moves": [],
        }
        return ensure_genre_genes(outline)
