"""State Extractor Agent — extracts state updates from chapter text.

Separated from Auditor so each agent focuses on one responsibility:
- Auditor: quality assessment (risk_level, issues)
- StateExtractor: state persistence (events, characters, objects, threads)
"""

import json
from typing import Any, Dict

from novel_agent.agents.base import PromptAgent
from novel_agent.json_utils import loads_json_object
from novel_agent.logging_config import get_logger

logger = get_logger("agents.state_extractor")

_STATE_EXTRACT_PROMPT = """你是一个状态提取专家。请从以下章节文本中提取所有需要持久化的状态更新信息。

## 提取要求
1. **events**：本章发生的关键事件（至少 1 个），每个需要 id、summary、相关角色/物品/线索
2. **characters**：角色状态变化（位置、情绪、身体状态）
3. **objects**：道具/物品的状态变化（持有者、状态）
4. **threads**：故事线状态（新开/推进/关闭）
5. **foreshadows**：伏笔（新埋/推进/回收）
6. **hooks**：钩子/悬念（新开/关闭）
7. **character_behaviors**：登场人物在本章展现出的关键性格特征、行为习惯、动作习惯或语言风格片段。每个片段包含角色名（character）、具体表现细节或口头禅（behavior）以及触发行为的情境（context）。
8. **character_memories**：登场人物在本章的经历与情感影响，每个记录包含角色名（character）、本章核心经历（summary，如“得知了父亲的死讯”）、以及在此情境下产生的情感/心理/性格上的影响与变化描述（emotional_impact，如“内心充满悲愤与复仇的执念，性格变得更加冷酷和警惕”）。
9. **character_relations**：登场人物在本章发生的人际关系改变或好感度变动。每个记录包含：源角色（source_char）、目标角色（target_char）、关系类型（relation_type，如“结盟”、“反目”、“好感提升”、“敌对”等）、好感/敌对程度数值（intensity，小数范围为 -1.0 到 1.0，1.0 代表生死之交，-1.0 代表不死不休，0.0 代表萍水相逢）、关系变化描述（description，简短的一句话描述关系的变化和原因）。

## 输出格式
只输出纯 JSON：
```json
{
  "events": [{"id": "E章节_序号", "summary": "事件描述", "characters": ["角色"], "objects": ["物品"], "threads": ["线索"]}],
  "characters": {"角色名": {"location": "位置", "emotion": "情绪", "physical_state": "身体状态"}},
  "objects": [{"id": "O_物品名", "name": "物品名", "holder": "持有者", "status": "状态"}],
  "threads": [{"id": "T_线索名", "name": "线索名", "status": "open/progressing/closed"}],
  "foreshadows": [{"id": "F_编号", "title": "伏笔名", "status": "open/progressing/resolved", "description": "描述"}],
  "hooks": [{"id": "H_编号", "title": "钩子名", "status": "open/resolved", "description": "描述"}],
  "character_behaviors": [{"character": "角色名", "behavior": "特色动作或口头禅描述", "context": "触发场景情境"}],
  "character_memories": [{"character": "角色名", "summary": "经历了什么核心事件", "emotional_impact": "产生的心灵/性格影响描述"}],
  "character_relations": [{"source_char": "角色A", "target_char": "角色B", "relation_type": "关系变化类型", "intensity": 0.5, "description": "因并肩战斗产生信任，好感大幅提升。"}]
}
```

重要：不要遗漏任何重要事件或角色状态变化。即使没有变化，events 也应至少记录一个本章核心事件。"""


class StateExtractorAgent(PromptAgent):
    """Extracts structured state updates from chapter text.

    Unlike the Auditor which focuses on quality assessment, this agent
    is specialized in identifying and structuring narrative state changes.
    """

    def __init__(self, llm, prompts=None):
        super().__init__("state_extractor", llm)
        self.prompts = prompts

    def _build_prompt(
        self, chapter_text: str, chapter_id: str, chapter_summary: str = ""
    ) -> str:
        prompt_tmpl = ""
        if self.prompts:
            prompt_tmpl = self.prompts.load("state_extractor")
        if not prompt_tmpl:
            prompt_tmpl = _STATE_EXTRACT_PROMPT
        parts = [prompt_tmpl]
        if chapter_summary:
            parts.append(f"\n\n## 章节总结\n{chapter_summary}")
        parts.append(f"\n\n## 章节正文（第 {chapter_id} 章）\n{chapter_text}")
        return "".join(parts)

    def _parse_and_validate_extraction(self, raw: str, chapter_id: str) -> Dict[str, Any]:
        try:
            result = loads_json_object(raw)
            result = self._validate(result, chapter_id)
            logger.info(
                "State extraction for chapter %s: %d events, %d characters",
                chapter_id,
                len(result.get("events", [])),
                len(result.get("characters", {})),
            )
            return result
        except Exception as exc:
            logger.error("Failed to parse state extractor output: %s", exc)
            return self._empty_state()

    def extract(
        self, chapter_text: str, chapter_id: str, chapter_summary: str = ""
    ) -> Dict[str, Any]:
        """Extract state updates from chapter text."""
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty chapter text for state extraction")
            return self._empty_state()
        prompt = self._build_prompt(chapter_text, chapter_id, chapter_summary)
        raw = self.run(prompt)
        return self._parse_and_validate_extraction(raw, chapter_id)

    async def aextract(
        self, chapter_text: str, chapter_id: str, chapter_summary: str = ""
    ) -> Dict[str, Any]:
        """Extract state updates from chapter text asynchronously."""
        if not chapter_text or not chapter_text.strip():
            logger.warning("Empty chapter text for state extraction")
            return self._empty_state()
        prompt = self._build_prompt(chapter_text, chapter_id, chapter_summary)
        raw = await self.arun(prompt)
        return self._parse_and_validate_extraction(raw, chapter_id)

    def _validate(self, result: Dict[str, Any], chapter_id: str) -> Dict[str, Any]:
        """Validate and fix common issues in extracted state."""
        # Ensure all required keys exist
        result.setdefault("events", [])
        result.setdefault("characters", {})
        result.setdefault("objects", [])
        result.setdefault("threads", [])
        result.setdefault("foreshadows", [])
        result.setdefault("hooks", [])
        result.setdefault("reader_promises", [])
        result.setdefault("secrets", [])
        result.setdefault("character_behaviors", [])
        result.setdefault("character_memories", [])
        result.setdefault("character_relations", [])

        # Validate events have IDs
        for i, event in enumerate(result["events"]):
            if isinstance(event, dict) and not event.get("id"):
                event["id"] = f"E{chapter_id}_{i + 1:03d}"
            if isinstance(event, dict):
                event.setdefault("summary", "")
                event.setdefault("characters", [])
                event.setdefault("objects", [])
                event.setdefault("threads", [])

        # Ensure characters is a dict
        if not isinstance(result["characters"], dict):
            result["characters"] = {}

        # Ensure character_behaviors is a list
        if not isinstance(result["character_behaviors"], list):
            result["character_behaviors"] = []

        # Ensure character_memories is a list
        if not isinstance(result["character_memories"], list):
            result["character_memories"] = []

        # Ensure character_relations is a list
        if not isinstance(result["character_relations"], list):
            result["character_relations"] = []

        return result

    @staticmethod
    def _empty_state() -> Dict[str, Any]:
        return {
            "events": [],
            "characters": {},
            "objects": [],
            "threads": [],
            "foreshadows": [],
            "hooks": [],
            "reader_promises": [],
            "secrets": [],
            "character_behaviors": [],
            "character_memories": [],
            "character_relations": [],
        }
