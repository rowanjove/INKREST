"""StoryContextResolver - Resolves context bundles, memory retrieval, and reference citations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.context.budgeter import approximate_tokens, truncate_to_tokens
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import ActiveEditorContext, CitationReference


class ResolvedContextBundle:
    def __init__(
        self,
        formatted_prompt_block: str,
        chips: List[Dict[str, str]],
        citations: List[CitationReference],
        total_chars: int,
        budget_breakdown: Optional[Dict[str, int]] = None,
    ):
        self.formatted_prompt_block = formatted_prompt_block
        self.chips = chips
        self.citations = citations
        self.total_chars = total_chars
        self.budget_breakdown = budget_breakdown or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chips": self.chips,
            "citations": [c.model_dump() for c in self.citations],
            "total_chars": self.total_chars,
            "budget_breakdown": self.budget_breakdown,
        }


class StoryContextResolver:
    def __init__(self, story_adapter: StoryAdapter):
        self.adapter = story_adapter
        self.store = AssistantStore(self.adapter.root_dir)

    def resolve(
        self,
        user_message: str,
        editor_context: Optional[ActiveEditorContext] = None,
        skill_id: Optional[str] = None,
    ) -> ResolvedContextBundle:
        chips: List[Dict[str, str]] = []
        prompt_sections: List[str] = []
        budget: Dict[str, int] = {
            "system_skill": 400,
            "editor_selection": 0,
            "chapter_outline": 0,
            "character_cards": 0,
            "story_memory": 0,
            "author_preferences": 0,
        }

        active_chapter_id = editor_context.chapter_id if editor_context else None
        selected_text = editor_context.selected_text if editor_context else None
        before_text = editor_context.cursor_before_text if editor_context else None
        after_text = editor_context.cursor_after_text if editor_context else None

        # 1. Author Preferences & Writing Habits (L1 Memory)
        try:
            prefs = self.store.list_preferences(
                project_id=editor_context.project_id if editor_context else None
            )
            if prefs:
                chips.append({
                    "type": "preference",
                    "label": f"偏好 ({len(prefs)}条)",
                    "id": "author_prefs",
                })
                pref_lines = [f"- [{p.preference_type}] {p.content}" for p in prefs[:5]]
                pref_block = "【作者写作偏好与行文禁忌】\n" + "\n".join(pref_lines)
                prompt_sections.append(pref_block)
                budget["author_preferences"] = approximate_tokens(pref_block)
        except Exception:
            pass

        # 2. Active Selection & Editor State (L0 Memory)
        selection_block_parts: List[str] = []
        if selected_text:
            chips.append({
                "type": "selection",
                "label": f"选区 ({len(selected_text)}字)",
                "id": "selection",
            })
            clean_sel = truncate_to_tokens(selected_text.strip(), 1200)
            selection_block_parts.append(f"【当前编辑器选中文本】\n```text\n{clean_sel}\n```")

        if before_text:
            clean_before = truncate_to_tokens(before_text[-1200:].strip(), 800)
            selection_block_parts.append(f"【选区/光标前文】\n{clean_before}")

        if after_text:
            clean_after = truncate_to_tokens(after_text[:600].strip(), 400)
            selection_block_parts.append(f"【选区/光标后文】\n{clean_after}")

        if selection_block_parts:
            sel_full = "\n\n".join(selection_block_parts)
            prompt_sections.append(sel_full)
            budget["editor_selection"] = approximate_tokens(sel_full)

        # 3. Chapter Outline & Context
        if active_chapter_id:
            chips.append({
                "type": "chapter",
                "label": f"第 {active_chapter_id} 章",
                "id": f"chapter_{active_chapter_id}",
            })
            ch_outline = self.adapter.get_chapter_outline(active_chapter_id)
            if ch_outline:
                chips.append({
                    "type": "outline",
                    "label": f"第 {active_chapter_id} 章纲",
                    "id": f"outline_{active_chapter_id}",
                })
                goal = ch_outline.get("goal") or ch_outline.get("summary") or ch_outline.get("title") or ""
                outline_block = f"【第 {active_chapter_id} 章章纲目标】\n{goal}"
                prompt_sections.append(outline_block)
                budget["chapter_outline"] = approximate_tokens(outline_block)

        # 4. Characters & World Constraints (L2 Project Facts / Canon)
        combined_text_for_search = f"{user_message} {selected_text or ''} {before_text or ''}"
        matched_chars = self.adapter.search_characters_in_text(combined_text_for_search)
        if not matched_chars:
            matched_chars = self.adapter.get_character_cards()[:3]

        char_lines: List[str] = []
        for char in matched_chars[:4]:
            cname = char.get("name") or char.get("id") or "未命名"
            chips.append({
                "type": "character",
                "label": f"人物：{cname}",
                "id": f"char_{char.get('id') or cname}",
            })
            profile = char.get("fixed_profile") or {}
            role = profile.get("role") or char.get("role") or "主要角色"
            motivation = profile.get("core_motivation") or char.get("motivation") or ""
            taboos = char.get("must_not") or []
            taboo_str = f"（禁忌：{', '.join(taboos[:2])}）" if taboos else ""
            char_lines.append(f"- {cname} [{role}]: 动机「{motivation}」{taboo_str}")

        if char_lines:
            char_block = "【相关人物卡档案】\n" + "\n".join(char_lines)
            prompt_sections.append(char_block)
            budget["character_cards"] = approximate_tokens(char_block)

        # 5. Hybrid Retrieval & Longform Story Memory (L3 Retrieval)
        # Bounded by before_chapter to prevent future info contamination
        mem_results = self.adapter.search_story_memory(
            user_message,
            before_chapter=active_chapter_id,
            limit=2,
        )
        if mem_results:
            mem_lines = []
            for item in mem_results:
                src_ch = item.get("source_chapter") or "前文"
                chips.append({
                    "type": "memory",
                    "label": f"前文第 {src_ch} 章",
                    "id": f"mem_ch_{src_ch}",
                })
                mem_lines.append(f"- [第{src_ch}章记忆]: {item.get('text', '')}")
            mem_block = "【前文相关剧情回忆 (FTS5)】\n" + "\n".join(mem_lines)
            prompt_sections.append(mem_block)
            budget["story_memory"] = approximate_tokens(mem_block)

        # 6. Citations Grounding
        citations = self.adapter.resolve_citations(
            query=user_message,
            mentioned_characters=[c.get("name") for c in matched_chars if c.get("name")],
            chapter_id=active_chapter_id,
        )

        full_prompt_block = "\n\n".join(prompt_sections)
        total_chars = len(full_prompt_block)
        budget["total_estimated"] = sum(budget.values())

        return ResolvedContextBundle(
            formatted_prompt_block=full_prompt_block,
            chips=chips,
            citations=citations,
            total_chars=total_chars,
            budget_breakdown=budget,
        )
