"""Context Builder Agent — assembles minimal context packs for scene writers.

Key features:
- Budget-aware assembly: prioritizes critical context, trims low-priority blocks
- Previous chapter tail injection for cross-chapter continuity
- Configurable MAX_CONTEXT_CHARS to prevent LLM context window overflow
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.control.constraint_synthesizer import synthesize_constraints
from novel_agent.control.scale_profile import is_vector_enabled_for_project
from novel_agent.control.narrative_debt import classify_debt
from novel_agent.logging_config import get_logger
from novel_agent.rules import RuleBook
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.vector_store import VectorStore, create_vector_store, apply_chapter_distance_penalty

logger = get_logger("agents.context_builder")

# Priority levels for context blocks (lower = more important, never trimmed at CRITICAL)
PRIORITY_CRITICAL = 0   # Scene card, chapter goal — never trimmed
PRIORITY_HIGH = 1       # Characters, current state
PRIORITY_MEDIUM = 2     # History, vector recall, prev chapter tail
PRIORITY_LOW = 3        # Timeline, world bible, style guide, rules

# Default max context size in Chinese characters (~1.5x tokens)
DEFAULT_MAX_CONTEXT_CHARS = 4000


class ContextBuilderAgent:
    """Builds the minimal context pack that is fed to a scene writer.

    Supports budget-aware assembly: when total context exceeds
    max_context_tokens, low-priority blocks are truncated or omitted.
    """

    def __init__(
        self,
        root_dir: Path,
        vector_store: Optional[VectorStore] = None,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ):
        self.root_dir = Path(root_dir)
        if vector_store is None:
            from novel_agent.services.embedding_policy import create_vector_store_for_project

            vector_store = create_vector_store_for_project(self.root_dir)
        self.vector_store = vector_store
        self.store = SQLiteStateStore(self.root_dir)
        self.max_context_chars = max_context_chars
        self._prev_summary_cache: Dict[str, str] = {}
        self._prev_tail_cache: Dict[str, str] = {}
        self._prev_chars_cache: Dict[str, List[str]] = {}
        
        # Load max_context_tokens from pipeline settings, default to 16000
        self.max_context_tokens = 16000
        try:
            from novel_agent.pipeline import load_pipeline_settings
            config = load_pipeline_settings(self.root_dir)
            tokens = config.get("chapter", {}).get("max_context_tokens") or config.get("runtime", {}).get("max_context_tokens")
            if tokens:
                self.max_context_tokens = int(tokens)
        except Exception:
            pass
    def build(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        """Build the full context pack for a scene.

        Assembles context blocks in priority order, trimming lower-priority
        blocks if total length exceeds max_context_chars.
        """
        # Gather all context blocks with priorities
        blocks: List[Tuple[str, str, int]] = []

        # --- CRITICAL: scene card and chapter goal (never trimmed) ---
        scene_block = self._build_scene_block(chapter_goal, scene)
        blocks.append(("场景信息", scene_block, PRIORITY_CRITICAL))

        # --- HIGH: characters, state, memories, constraints ---
        state = self._get_current_state(scene)
        blocks.extend(self._build_high_priority_blocks(scene, state))

        # --- MEDIUM: history, vector recall, prev chapter tail ---
        blocks.extend(self._build_medium_priority_blocks(chapter_goal, scene))

        # --- LOW: timeline, world, style, rules ---
        blocks.extend(self._build_low_priority_blocks(chapter_goal, scene))

        # Anti-AI guardrails — low priority so budget trimming drops this before scene/state
        if self._writer_anti_ai_enabled():
            anti_ai = self._build_writer_anti_ai_block()
            if anti_ai:
                blocks.append(("写作禁忌", anti_ai, PRIORITY_LOW))

        # Output requirements (always included)
        blocks.append(("输出要求", "只输出小说正文，不要标题，不要说明，不要 Markdown。", PRIORITY_CRITICAL))

        return self._assemble_with_budget(blocks)

    def _writer_anti_ai_enabled(self) -> bool:
        try:
            from novel_agent.pipeline import load_pipeline_settings

            chapter = load_pipeline_settings(self.root_dir).get("chapter", {}) or {}
            if "writer_anti_ai_hints" in chapter:
                return bool(chapter.get("writer_anti_ai_hints"))
            return True
        except Exception:
            return True

    def _build_writer_anti_ai_block(self) -> str:
        from novel_agent.quality.generation_policy import build_writer_anti_ai_block

        return build_writer_anti_ai_block(self.root_dir)

    def _get_current_state(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        state = self.store.get_continuity_state()
        state["secrets"] = self.store.list_secrets()
        current_chapter = str(scene.get("scene_id", "")).split("-")[0]
        state["reader_promises"] = classify_debt(
            self.store.list_reader_promises(), current_chapter
        )
        return state

    def _build_high_priority_blocks(self, scene: Dict[str, Any], state: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        blocks = []
        characters = self._prune_character_cards(scene)
        blocks.append(("人物资产", characters, PRIORITY_HIGH))

        state_text = json.dumps(state, ensure_ascii=False, indent=2)
        blocks.append(("当前状态", state_text, PRIORITY_HIGH))

        scene_chars = scene.get("characters", [])
        if isinstance(scene_chars, str):
            scene_chars = [scene_chars]
        char_memories_block = self._build_character_memories_block(scene_chars)
        if char_memories_block:
            blocks.append(("登场角色性格与近期记忆", char_memories_block, PRIORITY_HIGH))

        consistency_block = self._character_consistency_block(scene)
        if consistency_block:
            blocks.append(("角色性格行为一致性约束", consistency_block, PRIORITY_HIGH))

        debt_block = self._build_debt_block(scene)
        if debt_block:
            blocks.append(("剧情债务约束", debt_block, PRIORITY_HIGH))

        constraints = synthesize_constraints(state=state, recall_items=[], scene=scene)
        if constraints:
            blocks.append(("本章硬约束", self._bullets(constraints), PRIORITY_HIGH))
        return blocks

    def _build_medium_priority_blocks(self, chapter_goal: str, scene: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        blocks = []
        history = self._relevant_history(chapter_goal, scene)
        blocks.append(("相关历史事件", history, PRIORITY_MEDIUM))

        if is_vector_enabled_for_project(self.root_dir):
            vector_recall = self._vector_recall(chapter_goal, scene)
            blocks.append(("语义相关片段", vector_recall, PRIORITY_MEDIUM))

        prev_tail = self._get_previous_chapter_tail(scene)
        if prev_tail and prev_tail != "暂无。":
            blocks.append(("上一章尾段（衔接参考）", prev_tail, PRIORITY_MEDIUM))
        return blocks

    def _build_low_priority_blocks(self, chapter_goal: str, scene: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        blocks = []
        timeline = self._relevant_timeline(chapter_goal, scene)
        blocks.append(("相关时间线网络", timeline, PRIORITY_LOW))

        world = self._read_optional("assets/world_bible.md")
        blocks.append(("世界观", world, PRIORITY_LOW))

        style = self._read_optional("assets/style_guide.md")
        blocks.append(("文风规范", style, PRIORITY_LOW))

        writing_guide = self._read_optional("assets/writing_guide.md")
        blocks.append(("预设写作指南", writing_guide, PRIORITY_LOW))

        rules = RuleBook(self.root_dir).to_prompt_section()
        blocks.append(("写作规则", rules, PRIORITY_LOW))
        return blocks

    def _prune_character_cards(self, scene: Dict[str, Any]) -> str:
        """Load character_cards.yaml, parse it, and filter to keep only characters in the scene + protagonist."""
        cards_path = self.root_dir / "assets" / "character_cards.yaml"
        if not cards_path.exists():
            return "暂无。"
            
        import yaml
        try:
            content = cards_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content) or {}
        except Exception as e:
            logger.warning("Failed to parse character_cards.yaml: %s", e)
            return self._read_optional("assets/character_cards.yaml")
            
        characters_list = data.get("characters", [])
        if not characters_list:
            return "暂无。"
            
        scene_chars = scene.get("characters", [])
        if isinstance(scene_chars, str):
            scene_chars = [scene_chars]
        scene_chars = [str(c).strip() for c in scene_chars if str(c).strip()]
        
        # We always keep protagonist and their variants
        active_ids_names = {"protagonist", "主角"}
        for char in scene_chars:
            active_ids_names.add(char)
            
        filtered = []
        for char_card in characters_list:
            if not isinstance(char_card, dict):
                continue
            char_id = str(char_card.get("id", "")).strip()
            char_name = str(char_card.get("name", "")).strip()
            if char_id in active_ids_names or char_name in active_ids_names:
                filtered.append(char_card)
                
        if not filtered:
            return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            
        pruned_data = {"characters": filtered}
        return yaml.safe_dump(pruned_data, allow_unicode=True, sort_keys=False)

    def _build_scene_block(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        """Build the critical scene information block."""
        lines = [
            f"# Scene {scene.get('scene_id', 'unknown')} Context",
            "",
            "## 本章目标",
            chapter_goal,
            "",
            "## 当前场景",
            f"- 目的：{scene.get('purpose', '')}",
            f"- 入场：{scene.get('entry', '')}",
            f"- 出场：{scene.get('exit', '')}",
            f"- 目标字数：{scene.get('target_chars', '')}",
            "",
            "## 必须包含",
            self._bullets(scene.get("must_include", [])),
            "",
            "## 禁止事项",
            self._bullets(scene.get("must_not_include", [])),
        ]
        return "\n".join(lines)

    def _build_debt_block(self, scene: Dict[str, Any]) -> str:
        """Build narrative debt constraints block."""
        # Get open secrets (should not be revealed yet)
        open_secrets = self.store.list_secrets(status="hidden")
        # Get open reader promises (should be fulfilled)
        open_promises = self.store.list_reader_promises(status="open")

        if not open_secrets and not open_promises:
            return ""

        lines = []

        if open_secrets:
            lines.append("### 本章不可提前揭露")
            for secret in open_secrets[:5]:  # Limit to 5
                lines.append(f"- {secret['title']}: {secret['description']}")

        if open_promises:
            lines.append("### 已进入回收窗口")
            for promise in open_promises[:5]:  # Limit to 5
                lines.append(f"- {promise['title']}: {promise['description']}")

        return "\n".join(lines)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the token count of a given text.

        Calculates ~1.3 tokens per Chinese character and ~1.0 token per English word.
        If tiktoken is available, uses it for precise count.
        """
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            import re
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_words = len(re.findall(r'[a-zA-Z0-9]+', text))
            other_chars = len(text) - chinese_chars - english_words
            return int(chinese_chars * 1.3 + english_words * 1.0 + other_chars * 0.5)

    def _assemble_with_budget(self, blocks: List[Tuple[str, str, int]]) -> str:
        """Assemble context blocks respecting the token budget.

        Strategy:
        1. Always include CRITICAL blocks (no trimming)
        2. Add blocks in priority order
        3. When budget is exceeded, truncate the current block and skip remaining
        """
        # Sort by priority (lower number = higher priority)
        sorted_blocks = sorted(blocks, key=lambda b: b[2])

        total_tokens = 0
        assembled: List[str] = []
        budget = self.max_context_tokens
        trimmed_count = 0

        for title, content, priority in sorted_blocks:
            block_text = f"## {title}\n{content}" if title != "场景信息" else content
            block_tokens = self._estimate_tokens(block_text)

            if priority == PRIORITY_CRITICAL:
                # Always include critical blocks
                assembled.append(block_text)
                total_tokens += block_tokens
                continue

            remaining = budget - total_tokens
            if remaining <= 0:
                trimmed_count += 1
                continue

            if block_tokens > remaining:
                # Truncate this block to fit.
                # Assuming ~1.3 tokens per char for Chinese, we estimate char_len = remaining / 1.3
                char_len = int(remaining / 1.3)
                if char_len > 15:
                    truncated = block_text[:char_len - 15] + "\n\n…（已裁剪以控制上下文长度）"
                    assembled.append(truncated)
                    total_tokens += self._estimate_tokens(truncated)
                else:
                    trimmed_count += 1
                    continue
                trimmed_count += 1
                logger.info(
                    "Context block '%s' truncated (tokens: %d -> ~%d)",
                    title, block_tokens, remaining,
                )
            else:
                assembled.append(block_text)
                total_tokens += block_tokens

        if trimmed_count > 0:
            logger.info(
                "Context assembly: ~%d tokens total, %d blocks trimmed/omitted (budget=%d tokens)",
                total_tokens, trimmed_count, budget,
            )

        return "\n\n".join(assembled).strip() + "\n"

    def _get_prev_chapter_characters(self, prev_id: str) -> List[str]:
        cached = self._prev_chars_cache.get(prev_id)
        if cached is not None:
            return list(cached)

        # 1. 尝试从上一章的 plan.json 中读取最后一个场景的人物
        plan_path = self.root_dir / "workspace" / "chapters" / f"chapter_{prev_id}" / "plan.json"
        if plan_path.exists():
            try:
                import json
                plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
                scenes = plan_data.get("scenes", [])
                if scenes:
                    last_scene = scenes[-1]
                    chars = last_scene.get("characters", [])
                    if isinstance(chars, str):
                        chars = [chars]
                    found = [str(c).strip() for c in chars if str(c).strip()]
                    self._prev_chars_cache[prev_id] = found
                    return found
            except Exception:
                pass

        # 2. Fallback: 从数据库中查询所有的角色名字，并在前一章末尾 300 字里查找
        prev_txt_path = self.root_dir / "workspace" / "chapters" / f"chapter_{prev_id}" / "chapter_final.txt"
        if prev_txt_path.exists():
            try:
                text = prev_txt_path.read_text(encoding="utf-8").strip()
                tail_text = text[-300:] if len(text) > 300 else text
                
                # 查询 SQLite 中已注册的所有人物名字
                known_names = []
                try:
                    chars_dict = self.store.list_characters()
                    for char_id, char_info in chars_dict.items():
                        name = char_info.get("name")
                        if name:
                            known_names.append(str(name).strip())
                        known_names.append(str(char_id).strip())
                except Exception:
                    pass
                
                # 去重
                known_names = list(set(known_names))
                found_chars = []
                for name in known_names:
                    if name in tail_text:
                        found_chars.append(name)
                self._prev_chars_cache[prev_id] = found_chars
                return found_chars
            except Exception:
                pass

        self._prev_chars_cache[prev_id] = []
        return []

    def _get_previous_chapter_summary(self, prev_id: str) -> str:
        """Query SQLite or markdown file for the summary of the previous chapter."""
        cached = self._prev_summary_cache.get(prev_id)
        if cached is not None:
            return cached

        try:
            import sqlite3
            conn = sqlite3.connect(self.store.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "select summary from chapter_summaries where chapter_id = ?",
                    (prev_id,)
                ).fetchone()
                if row and row["summary"]:
                    summary = str(row["summary"]).strip()
                    self._prev_summary_cache[prev_id] = summary
                    return summary
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to query chapter summary for %s: %s", prev_id, e)
        
        # Fallback: 尝试读 workspace 下的 chapter_summary.md 文件
        summary_path = (
            self.root_dir
            / "workspace"
            / "chapters"
            / f"chapter_{prev_id}"
            / "chapter_summary.md"
        )
        if summary_path.exists():
            try:
                summary = summary_path.read_text(encoding="utf-8").strip()
                self._prev_summary_cache[prev_id] = summary
                return summary
            except Exception:
                pass
        self._prev_summary_cache[prev_id] = ""
        return ""

    def _scene_cast_set(self, scene: Dict[str, Any]) -> set:
        from novel_agent.services.continuity_pack import scene_cast_from_scene

        return {str(c).strip() for c in scene_cast_from_scene(scene) if str(c).strip()}

    def _detect_continuity_type(
        self, scene: Dict[str, Any], prev_id: str, *, chapter_opening: bool = False
    ) -> str:
        current_chars = self._scene_cast_set(scene)

        # 1. 视角切换判定：检查与前一章结尾登场人物是否有重合
        prev_chars = set(self._get_prev_chapter_characters(prev_id))

        # 只有在双方都有角色信息时才做排除。如果其中一方为空，出于连贯性起见，不作为视角切换处理
        if current_chars and prev_chars:
            if not current_chars.intersection(prev_chars):
                return "new_perspective"

        # 2. 时空跃迁判定：通过 entry 属性正则匹配跳转词
        entry_text = str(scene.get("entry", "")).strip()
        if entry_text:
            import re
            temporal_patterns = [
                r"(三天后|几天后|翌日|第二天|几个时辰|转眼|过了?许久|半个月|一年|眨眼间|某日|某天|清晨|黄昏|夜晚|深夜|日落|日出)",
                r"(回到|来到|抵达|在……里|出现在|已经?到|前往|踏入|踏上|启程)"
            ]
            for pattern in temporal_patterns:
                if re.search(pattern, entry_text):
                    return "temporal_gap"

        # 3. 默认紧密连贯
        return "continuous"

    def _get_previous_chapter_tail(self, scene: Dict[str, Any]) -> str:
        """Get the contextual connection info from the previous chapter."""
        scene_id = scene.get("scene_id", "")
        if not scene_id:
            return ""

        cache_key = str(scene_id)
        cached = self._prev_tail_cache.get(cache_key)
        if cached is not None:
            return cached

        # 只在新章节的第一个场景才需要衔接前一章
        scene_str = str(scene_id)
        if "-" in scene_str:
            parts = scene_str.split("-")
            scene_num = parts[1].strip().lstrip("0")
            if scene_num != "1":
                return ""

        try:
            # 兼容 chapter_002-01 或 002-01 格式
            chapter_part = scene_str.split("-")[0]
            chapter_num = int(chapter_part.lower().replace("chapter_", "").strip())
            if chapter_num <= 1:
                return ""
            prev_id = f"{chapter_num - 1:03d}"
        except (ValueError, IndexError):
            return ""

        chapter_opening = False
        if "-" in scene_str:
            scene_num = scene_str.split("-")[1].strip().lstrip("0")
            chapter_opening = scene_num in ("", "1")
        continuity_type = self._detect_continuity_type(
            scene, prev_id, chapter_opening=chapter_opening
        )
        logger.info("Scene %s detected continuity type: %s", scene_id, continuity_type)

        parts_info = []

        if continuity_type == "new_perspective":
            parts_info.append("【视角转换提示】\n当前场景为全新人物或视角镜头切换，上一章的角色和镜头暂时留在别处。请在了解前章大背景的前提下，合理开启新桥段。")
        elif continuity_type == "temporal_gap":
            summary = self._get_previous_chapter_summary(prev_id)
            if summary:
                parts_info.append(f"【前一章（第 {prev_id} 章）剧情梗概】\n{summary}")
            parts_info.append("【时空跃迁衔接背景与过渡说明】\n本章与前一章之间存在时间或空间的跃迁/跳跃，请在写作时合理交代背景的过渡与转变。")
        else:
            summary = self._get_previous_chapter_summary(prev_id)
            if summary:
                parts_info.append(f"【前一章（第 {prev_id} 章）剧情梗概】\n{summary}")
            
            prev_path = (
                self.root_dir
                / "workspace"
                / "chapters"
                / f"chapter_{prev_id}"
                / "chapter_final.txt"
            )
            if prev_path.exists():
                try:
                    text = prev_path.read_text(encoding="utf-8").strip()
                    tail = text[-500:] if len(text) > 500 else text
                    parts_info.append(f"【时序无缝衔接参考 | 第 {prev_id} 章结尾段落】\n{tail}\n（请在此段落基础上，进行无缝的时序与剧情延续，保持笔触和镜头连贯）")
                except Exception:
                    pass

        if parts_info:
            result = "\n\n".join(parts_info)
            self._prev_tail_cache[cache_key] = result
            return result
        self._prev_tail_cache[cache_key] = ""
        return ""

    def _read_optional(self, relative_path: str) -> str:
        path = self.root_dir / relative_path
        if not path.exists():
            return "暂无。"
        return path.read_text(encoding="utf-8").strip() or "暂无。"

    @staticmethod
    def _bullets(items) -> str:
        if not items:
            return "- 无"
        return "\n".join(f"- {item}" for item in items)

    def _relevant_history(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        terms = [chapter_goal]
        terms.extend(scene.get("must_include", []))
        terms.extend(scene.get("characters", []))
        terms.extend(scene.get("objects", []))
        terms.extend(scene.get("threads", []))
        seen = set()
        lines = []
        for term in terms:
            for event in self.store.search_events(str(term), limit=3):
                if event["id"] in seen:
                    continue
                seen.add(event["id"])
                lines.append(
                    f"- 第 {event['chapter_id']} 章 / {event['id']}：{event['summary']}"
                )
        return "\n".join(lines) if lines else "- 暂无"

    def _relevant_timeline(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        terms = [chapter_goal]
        terms.extend(scene.get("must_include", []))
        terms.extend(scene.get("characters", []))
        terms.extend(scene.get("objects", []))
        terms.extend(scene.get("threads", []))
        seen = set()
        lines = []
        for term in terms:
            for item in self.store.search_timeline(str(term), limit=4):
                if item["id"] in seen:
                    continue
                seen.add(item["id"])
                lines.append(f"- {self._format_timeline_item(item)}")
        return "\n".join(lines) if lines else "- 暂无"

    @staticmethod
    def _format_timeline_item(item: Dict[str, Any]) -> str:
        kind = item.get("kind")
        if kind == "node":
            return (
                f"节点/{item.get('type', '')}/{item.get('name', '')}"
                f"：{item.get('description', '')}"
            )
        if kind == "edge":
            return (
                f"关系/{item.get('from', '')} -> {item.get('to', '')}"
                f"：{item.get('description', '')}"
            )
        if kind == "foreshadow":
            return (
                f"伏笔/{item.get('status', '')}/{item.get('title', '')}"
                f"：{item.get('description', '')}"
            )
        if kind == "hook":
            return (
                f"钩子/{item.get('status', '')}/{item.get('title', '')}"
                f"：{item.get('description', '')}"
            )
        return str(item)

    def _vector_recall(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        """Semantic search for relevant snippets from the vector store."""
        query_parts = [chapter_goal]
        query_parts.extend(scene.get("must_include", []))
        query = " ".join(str(p) for p in query_parts)
        if not query.strip():
            return "- 暂无"

        current_chapter = scene.get("chapter_id", "")
        if not current_chapter and "scene_id" in scene:
            current_chapter = str(scene["scene_id"]).split("-")[0]

        from novel_agent.control.long_run import resolve_vector_search_window

        window = resolve_vector_search_window(self.root_dir)
        raw_results = self.vector_store.search(
            query,
            top_k=15,
            near_chapter_id=current_chapter or None,
            chapter_window=window,
        )
        if not raw_results:
            return "- 暂无"

        # Apply distance penalty to filter and label results
        results = apply_chapter_distance_penalty(
            raw_results, current_chapter, top_k=5
        )

        lines = []
        for r in results:
            meta = r.get("metadata", {})
            chapter = meta.get("chapter", "?")
            scene_id = meta.get("scene_id", "")
            rewrite_hint = r.get("rewrite_hint")
            label = f"第 {chapter} 章"
            if scene_id:
                label += f" / 场景 {scene_id}"
            if rewrite_hint:
                label += f" / 需改写引用"
            lines.append(f"- [{label}] {r['text'][:200]}")
        return "\n".join(lines)

    def _character_consistency_block(self, scene: Dict[str, Any]) -> str:
        """Retrieve and compile character consistency constraints for current scene."""
        characters = scene.get("characters", [])
        if not characters:
            return ""
        if isinstance(characters, str):
            characters = [characters]

        purpose = scene.get("purpose", "")
        must_include = " ".join(scene.get("must_include", []))
        query = f"{purpose} {must_include}"

        lines = []
        for char in characters:
            char = str(char).strip()
            if not char:
                continue

            from novel_agent.control.long_run import resolve_vector_search_window

            ch = str(scene.get("chapter_id") or "").split("-")[0] or None
            window = resolve_vector_search_window(self.root_dir)
            results = self.vector_store.search(
                query=query,
                top_k=3,
                filters={"type": "character_behavior", "character": char},
                near_chapter_id=ch,
                chapter_window=window,
            )
            if results:
                lines.append(f"### 角色 [{char}] 的一致性行为特征")
                for r in results:
                    lines.append(f"- 习惯表现：{r['text']}")
                    if r.get("metadata", {}).get("context"):
                        lines.append(f"  (情境参考：{r['metadata']['context']})")

        if not lines:
            return ""
        return "\n".join(lines)

    def _build_character_memories_block(self, scene_chars: List[str]) -> str:
        if not scene_chars:
            return ""
        mem_path = self.root_dir / "assets" / "character_memories.yaml"
        if not mem_path.exists():
            return ""
        import yaml
        try:
            data = yaml.safe_load(mem_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return ""
        chars_data = data.get("characters", {})
        if not chars_data:
            return ""
        
        lines = []
        for char_name in scene_chars:
            char_name = str(char_name).strip()
            if char_name not in chars_data:
                continue
            char_info = chars_data[char_name]
            lines.append(f"### 角色：{char_name}")
            core_traits = char_info.get("core_traits", [])
            if core_traits:
                lines.append("  * 核心性格特征：")
                for trait in core_traits:
                    lines.append(f"    - {trait}")
            speech_patterns = char_info.get("speech_patterns", [])
            if speech_patterns:
                lines.append("  * 言语风格/套路：")
                for pat in speech_patterns:
                    lines.append(f"    - {pat}")
            memories = char_info.get("memories", [])
            if memories:
                recent = memories[-3:]
                lines.append("  * 近期记忆与经历影响：")
                for mem in recent:
                    if isinstance(mem, dict):
                        lines.append(f"    - 经历：{mem.get('summary', '')} | 心理/影响：{mem.get('emotional_impact', '')}")
        if not lines:
            return ""
        return "\n".join(lines)
