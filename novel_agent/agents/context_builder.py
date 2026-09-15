"""Context Builder Agent — assembles minimal context packs for scene writers.

Key features:
- Budget-aware assembly: prioritizes critical context, trims low-priority blocks
- Previous chapter tail injection for cross-chapter continuity
- Configurable MAX_CONTEXT_CHARS to prevent LLM context window overflow
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from novel_agent.control.constraint_synthesizer import synthesize_constraints
from novel_agent.control.scale_profile import is_vector_enabled_for_project
from novel_agent.control.longform_flags import flag_enabled
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
        # Exposed for generation/audit/style stages to bind their role to the
        # exact pack emitted by the writer context build.
        self.last_context_pack_id = ""
        
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
    def build(
        self,
        chapter_goal: str,
        scene: Dict[str, Any],
        *,
        plan: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Build the full context pack for a scene.

        Assembles context blocks in priority order, trimming lower-priority
        blocks if total length exceeds max_context_chars.
        """
        # Gather all context blocks with priorities
        blocks: List[Tuple[str, str, int]] = []

        # --- CRITICAL: scene card and chapter goal (never trimmed) ---
        scene_block = self._build_scene_block(chapter_goal, scene)
        blocks.append(("场景信息", scene_block, PRIORITY_CRITICAL))
        live_state = self._build_live_character_state_block(scene)
        if live_state:
            blocks.append(("在场人物状态", live_state, PRIORITY_CRITICAL))

        try:
            from novel_agent.agents.writer_task_card import (
                build_writer_task_card,
                format_writer_task_card,
            )

            card_text = format_writer_task_card(build_writer_task_card(plan, scene))
            if card_text:
                blocks.append(("写前任务卡", card_text, PRIORITY_CRITICAL))
        except Exception:
            logger.debug("Writer task card skipped", exc_info=True)

        # --- HIGH: characters, state, memories, constraints ---
        state = self._get_current_state(scene)
        blocks.extend(self._build_high_priority_blocks(scene, state, plan=plan))

        try:
            from novel_agent.services.hierarchical_summary import assemble_hierarchical_context

            chapter_id = str(
                (plan or {}).get("chapter_id")
                or scene.get("chapter_id")
                or scene.get("scene_id")
                or "1"
            )
            packed = assemble_hierarchical_context(self.root_dir, chapter_id)
            hierarchy = str(packed.get("compiled_prompt_block") or "").strip()
            if hierarchy:
                blocks.append(("分层叙事蓝图", hierarchy, PRIORITY_HIGH))
        except Exception:
            pass

        # --- MEDIUM: history, vector recall, prev chapter tail ---
        blocks.extend(self._build_medium_priority_blocks(chapter_goal, scene))

        # --- LOW: timeline, world, style, rules ---
        blocks.extend(self._build_low_priority_blocks(chapter_goal, scene))

        # Anti-AI guardrails — low priority so budget trimming drops this before scene/state
        if self._writer_anti_ai_enabled():
            anti_ai = self._build_writer_anti_ai_block(scene=scene, plan=plan)
            if anti_ai:
                blocks.append(("写作禁忌", anti_ai, PRIORITY_LOW))

        # Output requirements (always included)
        blocks.append(("输出要求", "只输出小说正文，不要标题，不要说明，不要 Markdown。", PRIORITY_CRITICAL))

        assembled = self._assemble_with_budget(blocks)
        self._persist_context_pack_contract(scene, assembled)
        return assembled

    def _persist_context_pack_contract(self, scene: Mapping[str, Any], context_text: str) -> None:
        """Persist bounded Context Pack identity metadata for downstream stages."""

        try:
            from novel_agent.retrieval.context_contract import (
                bind_context_role,
                context_pack_id,
                save_context_pack_contract,
            )

            scene_id = str(scene.get("scene_id") or scene.get("id") or "chapter")
            chapter_id = str(scene.get("chapter_id") or scene_id.split("-")[0]).strip()
            if not chapter_id:
                return
            required_ids = scene.get("required_memory_ids") or []
            if isinstance(required_ids, str):
                required_ids = [required_ids]
            content_lock_id = ""
            # The content lock is already persisted by _build_content_lock_block;
            # link to its digest without copying the full contract into the pack.
            safe_scene = re.sub(r"[^A-Za-z0-9_.-]+", "_", scene_id)
            lock_path = (
                self.root_dir
                / "workspace"
                / "chapters"
                / f"chapter_{chapter_id}"
                / "reports"
                / f"scene_{safe_scene}_render_contract.json"
            )
            try:
                render_contract = json.loads(lock_path.read_text(encoding="utf-8"))
                lock = render_contract.get("content_lock") if isinstance(render_contract, Mapping) else {}
                if isinstance(lock, Mapping):
                    content_lock_id = str(lock.get("lock_digest") or render_contract.get("contract_id") or "")
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                pass
            pack_id = context_pack_id(
                chapter_id=chapter_id,
                scene_id=scene_id,
                context_text=context_text,
                required_memory_ids=[str(item) for item in required_ids],
                content_lock_id=content_lock_id,
            )
            save_context_pack_contract(
                self.root_dir,
                {
                    "pack_id": pack_id,
                    "chapter_id": chapter_id,
                    "scene_id": scene_id,
                    "context_sha256": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
                    "content_lock_id": content_lock_id,
                    "required_memory_ids": required_ids,
                    "coverage": {"chars": len(context_text), "max_chars": self.max_context_chars},
                    "status": "ready",
                    "route_hits": {"context_builder": "assembled"},
                    "roles": ["writer"],
                },
            )
            bind_context_role(self.root_dir, chapter_id, role="writer", pack_id=pack_id)
            self.last_context_pack_id = pack_id
        except Exception as exc:
            # Provenance must never make a normal generation unavailable.
            logger.debug("Failed to persist Context Pack contract: %s", exc)

    def _writer_anti_ai_enabled(self) -> bool:
        try:
            from novel_agent.pipeline import load_pipeline_settings

            chapter = load_pipeline_settings(self.root_dir).get("chapter", {}) or {}
            if "writer_anti_ai_hints" in chapter:
                return bool(chapter.get("writer_anti_ai_hints"))
            return True
        except Exception:
            return True

    def _build_writer_anti_ai_block(
        self,
        scene: Optional[Mapping[str, Any]] = None,
        plan: Optional[Mapping[str, Any]] = None,
    ) -> str:
        from novel_agent.quality.generation_policy import build_writer_anti_ai_block

        return build_writer_anti_ai_block(self.root_dir, scene=scene, plan=plan)

    def _get_current_state(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        state = self.store.get_continuity_state()
        state["secrets"] = self.store.list_secrets()
        current_chapter = str(scene.get("scene_id", "")).split("-")[0]
        state["reader_promises"] = classify_debt(
            self.store.list_reader_promises(), current_chapter
        )
        return state

    def _build_high_priority_blocks(
        self,
        scene: Dict[str, Any],
        state: Dict[str, Any],
        *,
        plan: Optional[Mapping[str, Any]] = None,
    ) -> List[Tuple[str, str, int]]:
        blocks = []
        characters = self._prune_character_cards(scene)
        blocks.append(("人物资产", characters, PRIORITY_HIGH))

        try:
            from novel_agent.services.realm_quarantine import build_realm_quarantine_hint

            chapter_id = str(
                (plan or {}).get("chapter_id")
                or scene.get("chapter_id")
                or str(scene.get("scene_id") or "").split("-")[0]
            )
            hint = build_realm_quarantine_hint(self.root_dir, chapter_id)
            if hint:
                blocks.append(("世界域隔离", hint, PRIORITY_HIGH))
        except Exception:
            logger.debug("Realm quarantine hint skipped", exc_info=True)

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

        expression_block = self._build_expression_avoidance_block(scene)
        if expression_block:
            blocks.append(("近期表达复读规避", expression_block, PRIORITY_HIGH))

        content_lock_block = self._build_content_lock_block(
            scene,
            state,
            plan=plan,
            expression_contract=expression_block,
        )
        if content_lock_block:
            blocks.append(("场景 CONTENT_LOCK", content_lock_block, PRIORITY_HIGH))

        voice_block = self._build_character_voice_block(scene)
        if voice_block:
            blocks.append(("角色声口约束", voice_block, PRIORITY_HIGH))

        evidence_block = self._build_event_evidence_block(scene)
        if evidence_block:
            blocks.append(("来源化剧情硬事实", evidence_block, PRIORITY_HIGH))

        constraints = synthesize_constraints(state=state, recall_items=[], scene=scene)
        if constraints:
            blocks.append(("本章硬约束", self._bullets(constraints), PRIORITY_HIGH))
        return blocks

    def _build_content_lock_block(
        self,
        scene: Dict[str, Any],
        state: Mapping[str, Any],
        *,
        plan: Optional[Mapping[str, Any]] = None,
        expression_contract: str = "",
    ) -> str:
        """Compile and persist the scene's source-bound content contract."""

        try:
            from novel_agent.prompt_registry import inspect_prompt_sources
            from novel_agent.quality.prose_identity import load_prose_identity_profile
            from novel_agent.quality.render_contract import (
                build_scene_render_contract,
                persist_render_contract,
            )

            chapter_id = str(scene.get("chapter_id") or scene.get("scene_id", "")).split("-")[0]
            if not chapter_id:
                return ""
            prompt_meta = inspect_prompt_sources(self.root_dir, "writer")
            profile = load_prose_identity_profile(self.root_dir) or {}
            contract = build_scene_render_contract(
                chapter_id=chapter_id,
                scene=scene,
                plan=plan,
                state_snapshot=state,
                prose_profile=profile,
                prompt_template_version=str(prompt_meta.get("selected_sha256") or ""),
                source_memory_ids=scene.get("source_memory_ids") or [],
                required_memory_ids=scene.get("required_memory_ids") or [],
                expression_contract=expression_contract,
            )
            scene_id = re.sub(
                r"[^A-Za-z0-9_.-]+",
                "_",
                str(scene.get("scene_id") or "scene"),
            )
            contract_path = (
                self.root_dir
                / "workspace"
                / "chapters"
                / f"chapter_{chapter_id}"
                / "reports"
                / f"scene_{scene_id}_render_contract.json"
            )
            persist_render_contract(
                contract_path,
                contract,
                metadata={"chapter_id": chapter_id, "scene_id": scene_id, "stage": "scene_generation"},
            )
            lock = dict(contract.content_lock or {})
            lock.pop("bindings", None)
            return (
                "[CONTENT_LOCK]\n"
                + json.dumps(
                    {
                        "contract_id": contract.contract_id,
                        "lock_digest": lock.get("lock_digest", ""),
                        "lock": lock,
                        "bindings": contract.bindings,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n[/CONTENT_LOCK]"
            )
        except Exception as exc:
            logger.debug("Failed to build scene content lock: %s", exc)
            return ""

    def _build_expression_avoidance_block(self, scene: Dict[str, Any]) -> str:
        """Inject only a bounded, source-labelled expression avoidance list."""

        chapter_id = str(scene.get("chapter_id") or scene.get("scene_id", "")).split("-")[0]
        if not chapter_id:
            return ""
        try:
            from novel_agent.quality.scene_expression import build_scene_expression_contract

            return build_scene_expression_contract(self.root_dir, chapter_id, scene, limit=10)
        except Exception as exc:
            logger.debug("Failed to build expression avoidance context: %s", exc)
            return ""

    def _build_event_evidence_block(self, scene: Dict[str, Any]) -> str:
        """Fuse adjacent/entity/semantic/open-thread evidence into a short block."""

        try:
            from novel_agent.quality.event_memory import (
                build_event_evidence_context,
                load_narrative_event_projections,
            )

            current = str(scene.get("chapter_id") or scene.get("scene_id", "")).split("-")[0]
            try:
                current_number = int("".join(char for char in current if char.isdigit()))
            except ValueError:
                current_number = None
            events = self.store.list_narrative_events(limit=160)
            if not events:
                historical = self.store.list_narrative_events(limit=1, include_superseded=True)
                if not historical:
                    # Existing projects may have the JSON projection before the
                    # SQLite backfill runs.  It is a read-only compatibility path.
                    events = load_narrative_event_projections(self.root_dir)
            events = [
                event
                for event in events
                if not event.get("superseded") and not event.get("superseded_by")
            ]
            if current_number is not None:
                events = [
                    event
                    for event in events
                    if not str(event.get("chapter_id") or "").isdigit()
                    or int(event.get("chapter_id")) < current_number
                ]

            scene_chars = scene.get("characters", [])
            scene_objects = scene.get("objects", [])
            scene_threads = scene.get("threads", [])
            if isinstance(scene_chars, str):
                scene_chars = [scene_chars]
            if isinstance(scene_objects, str):
                scene_objects = [scene_objects]
            if isinstance(scene_threads, str):
                scene_threads = [scene_threads]
            try:
                from novel_agent.retrieval.entity_index import (
                    build_entity_alias_map,
                    expand_entity_tokens,
                )

                alias_map = build_entity_alias_map(self.store)
                scene_chars = expand_entity_tokens(scene_chars, alias_map)
                scene_objects = expand_entity_tokens(scene_objects, alias_map)
                scene_threads = expand_entity_tokens(scene_threads, alias_map)
            except Exception:
                logger.debug("Entity alias expansion skipped", exc_info=True)

            # M3 canon visibility is deterministic and fail-closed for future,
            # superseded, invalidated, or unknowable character-belief facts.
            if flag_enabled("m3_canon_engine", self.root_dir):
                try:
                    from novel_agent.quality.canon_engine import filter_visible_canon

                    events, _canon_violations = filter_visible_canon(
                        events,
                        current_chapter=current or "",
                        known_character_ids={str(item) for item in scene_chars},
                    )
                except Exception as exc:
                    logger.debug("Canon visibility filtering unavailable: %s", exc)

            selected: Dict[str, str] = {}
            hybrid_routes: Dict[str, List[Dict[str, Any]]] = {
                "adjacent": [], "entity": [], "vector": [], "fts": []
            }

            def add(route: str, key: str, text: str) -> None:
                if text.strip():
                    selected.setdefault(f"{route}:{key}", f"[{route}] {text}")

            # Route 1: deterministic chapter adjacency.  This gives the writer
            # the latest state transition even when no entity was named in the
            # scene card.
            def chapter_value(item: Mapping[str, Any]) -> int:
                raw = str(item.get("chapter_id") or "")
                return int(raw) if raw.isdigit() else -1

            adjacent = sorted(events, key=chapter_value, reverse=True)
            for item in adjacent[:4]:
                context = build_event_evidence_context([item], limit=1)
                if context:
                    add("邻近事件", str(item.get("event_id") or item.get("id") or "?"), context[0]["text"])
                    hybrid_routes["adjacent"].append({
                        "memory_id": str(item.get("event_id") or item.get("id") or ""),
                        "kind": "event", "text": context[0]["text"],
                        "source_chapter": str(item.get("chapter_id") or ""),
                        "hardness": "required" if item.get("hardness") == "required" else "supporting",
                    })

            # Route 2: deterministic entity/relationship matches.
            filters = [
                ("actor", item) for item in scene_chars
            ] + [
                ("object_name", item) for item in scene_objects
            ] + [
                ("thread", item) for item in scene_threads
            ]
            if not filters:
                filters = [("actor", None)]
            for key, value in filters:
                kwargs = {"limit": 8, key: value}
                for item in build_event_evidence_context(events, **kwargs):
                    add("实体关联", item["event_id"], item["text"])
                    hybrid_routes["entity"].append({
                        "memory_id": str(item.get("event_id") or ""),
                        "kind": "event", "text": str(item.get("text") or ""),
                        "source_chapter": str(item.get("chapter_id") or ""),
                    })

            # Route 3: semantic event recall.  Vector failures are deliberately
            # ignored; deterministic routes remain useful offline.
            query_parts = [
                scene.get("purpose"),
                scene.get("goal"),
                scene.get("chapter_goal"),
                *scene_chars,
                *scene_objects,
                *scene_threads,
            ]
            query = " ".join(str(item) for item in query_parts if str(item or "").strip())
            if query:
                try:
                    from novel_agent.control.long_run import resolve_vector_search_window

                    results = self.vector_store.search(
                        query=query,
                        top_k=6,
                        filters={"type": "event"},
                        near_chapter_id=current or None,
                        chapter_window=resolve_vector_search_window(self.root_dir),
                    )
                    for item in results or []:
                        meta = item.get("metadata") or {}
                        result_chapter = str(meta.get("chapter") or meta.get("chapter_id") or "?")
                        hybrid_routes["vector"].append({
                            "memory_id": str(item.get("id") or result_chapter),
                            "kind": "event", "text": str(item.get("text") or ""),
                            "source_chapter": result_chapter,
                        })
                        add(
                            "语义事件",
                            str(item.get("id") or result_chapter),
                            f"[硬事实][event:{item.get('id', '?')}][第{result_chapter}章] {str(item.get('text') or '')[:180]}",
                        )
                except Exception as exc:
                    logger.debug("Semantic event recall unavailable: %s", exc)

                # Route 3b: SQLite FTS5 proper-noun recall.  Chinese unicode61
                # matching transparently falls back to the bounded projection
                # LIKE pass in SearchRepositoryMixin.
                if flag_enabled("m2_hybrid_retrieval", self.root_dir):
                    try:
                        for item in self.store.search_story(
                            query,
                            limit=6,
                            before_chapter=current or None,
                        ):
                            hybrid_routes["fts"].append({
                                "memory_id": str(item.get("memory_id") or ""),
                                "kind": str(item.get("kind") or "memory"),
                                "text": str(item.get("text") or ""),
                                "source_chapter": str(item.get("source_chapter") or ""),
                                "source_revision_id": str(item.get("source_revision_id") or ""),
                                "hardness": str(item.get("hardness") or "supporting"),
                                "superseded": bool(item.get("superseded")),
                            })
                            add(
                                "关键词检索",
                                str(item.get("memory_id") or "?"),
                                f"[{item.get('hardness', 'supporting')}]"
                                f"[{item.get('memory_id', '?')}] {str(item.get('text') or '')[:180]}",
                            )
                    except Exception as exc:
                        logger.debug("SQLite FTS recall unavailable: %s", exc)

                # M2 is opt-in.  Fuse the same bounded routes into a required-
                # aware Context Pack so a high-priority fact cannot disappear
                # merely because a vector/FTS route ranks distractors first.
                if flag_enabled("m2_hybrid_retrieval", self.root_dir):
                    try:
                        from novel_agent.retrieval.context_pack import build_context_pack
                        from novel_agent.retrieval.hybrid import hybrid_search
                        from novel_agent.retrieval.reranker import deterministic_rerank

                        fused = hybrid_search(
                            self.store,
                            query,
                            before_chapter=current or None,
                            route_results={name: values for name, values in hybrid_routes.items() if values},
                            limit=12,
                        )
                        fused = deterministic_rerank(fused, limit=12)
                        required_ids = scene.get("required_memory_ids") or []
                        pack = build_context_pack(
                            fused,
                            required_memory_ids=[str(item) for item in required_ids],
                            max_chars=min(self.max_context_chars, 4000),
                        )
                        try:
                            retrieval_report = self.root_dir / "workspace" / "reports" / "retrieval_latest.json"
                            retrieval_report.parent.mkdir(parents=True, exist_ok=True)
                            retrieval_report.write_text(
                                json.dumps(
                                    {
                                        "chapter_id": current,
                                        "coverage": pack.get("coverage"),
                                        "status": pack.get("status"),
                                        "missing_required_memory_ids": pack.get("missing_required_memory_ids") or [],
                                        "route_hits": pack.get("route_hits") or {},
                                        "candidate_count": len(fused),
                                    },
                                    ensure_ascii=False,
                                ),
                                encoding="utf-8",
                            )
                        except OSError:
                            pass
                        if pack.get("text"):
                            add(
                                "混合检索",
                                "context-pack",
                                f"[coverage:{pack.get('coverage', 1.0)}] {pack['text'][:1200]}",
                            )
                    except Exception as exc:
                        logger.debug("Hybrid context pack unavailable: %s", exc)

            # Route 4: open threads/debts are not events, but are narrative
            # constraints that should accompany event evidence.
            debt_rows = [
                ("伏笔", self.store.list_foreshadows()),
                ("钩子", self.store.list_hooks()),
                ("秘密", self.store.list_secrets()),
            ]
            for debt_kind, rows in debt_rows:
                for item in rows:
                    status = str(item.get("status") or "").lower()
                    if status not in {"open", "hidden", "active", "pending"}:
                        continue
                    related = item.get("related_characters") or []
                    if scene_chars and related and not set(map(str, scene_chars)).intersection(map(str, related)):
                        continue
                    add(
                        "开放线程",
                        f"{debt_kind}:{item.get('id', '?')}",
                        f"[{debt_kind}:{item.get('id', '?')}][第{item.get('chapter_id', '?')}章] "
                        f"{item.get('title', '')}：{item.get('description', '')}",
                    )

            return "\n".join(list(selected.values())[:12])
        except Exception as exc:
            logger.debug("Failed to build event evidence context: %s", exc)
            return ""

    def _build_character_voice_block(self, scene: Dict[str, Any]) -> str:
        scene_chars = scene.get("characters", [])
        if isinstance(scene_chars, str):
            scene_chars = [scene_chars]
        if not scene_chars:
            return ""
        try:
            from novel_agent.quality.character_voice import build_character_voice_context

            return build_character_voice_context(self.root_dir, [str(item) for item in scene_chars])
        except Exception as exc:
            logger.debug("Failed to build character voice context: %s", exc)
            return ""

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

    def _build_live_character_state_block(self, scene: Dict[str, Any]) -> str:
        scene_chars = scene.get("characters", [])
        if isinstance(scene_chars, str):
            scene_chars = [scene_chars]
        if not scene_chars:
            return ""
        try:
            from novel_agent.retrieval.entity_index import (
                build_entity_alias_map,
                format_live_character_state,
            )

            characters = self.store.list_characters()
            return format_live_character_state(
                characters,
                scene_chars,
                build_entity_alias_map(self.store),
            )
        except Exception:
            logger.debug("Live character state skipped", exc_info=True)
            return ""

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
        total_chars = 0
        assembled: List[str] = []
        budget = self.max_context_tokens
        char_budget = max(1, int(self.max_context_chars))
        trimmed_count = 0

        for title, content, priority in sorted_blocks:
            block_text = f"## {title}\n{content}" if title != "场景信息" else content
            block_tokens = self._estimate_tokens(block_text)

            if priority == PRIORITY_CRITICAL:
                # Always include critical blocks
                assembled.append(block_text)
                total_tokens += block_tokens
                total_chars += len(block_text)
                continue

            remaining = budget - total_tokens
            remaining_chars = char_budget - total_chars
            if remaining <= 0 or remaining_chars <= 0:
                trimmed_count += 1
                continue

            if block_tokens > remaining or len(block_text) > remaining_chars:
                # Truncate this block to fit.
                # Assuming ~1.3 tokens per char for Chinese, we estimate char_len = remaining / 1.3
                char_len = min(int(remaining / 1.3), remaining_chars)
                if char_len > 15:
                    truncated = block_text[:char_len - 15] + "\n\n…（已裁剪以控制上下文长度）"
                    assembled.append(truncated)
                    total_tokens += self._estimate_tokens(truncated)
                    total_chars += len(truncated)
                else:
                    trimmed_count += 1
                    continue
                trimmed_count += 1
                reason = (
                    "Token 预算与字符预算均不足"
                    if (block_tokens > remaining and len(block_text) > remaining_chars)
                    else ("Token 预算不足" if block_tokens > remaining else "字符预算不足")
                )
                logger.info(
                    "Context block '%s' truncated: reason=%s, original_chars=%d, "
                    "kept_chars=%d, original_tokens~%d, kept_tokens~%d, "
                    "remaining_token_budget=%d, remaining_char_budget=%d",
                    title,
                    reason,
                    len(block_text),
                    len(truncated) if char_len > 15 else 0,
                    block_tokens,
                    self._estimate_tokens(truncated) if char_len > 15 else 0,
                    remaining,
                    remaining_chars,
                )
            else:
                assembled.append(block_text)
                total_tokens += block_tokens
                total_chars += len(block_text)

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
        if plan_path.is_file():
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
        from novel_agent.services.manuscript_workspace import read_chapter_plain_text

        text = read_chapter_plain_text(self.root_dir, prev_id).strip()
        if text:
            try:
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

        db_path = getattr(self.store, "db_path", None)
        if isinstance(db_path, (str, Path)) and Path(db_path).is_file():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path), timeout=10.0)
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
        if summary_path.is_file():
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
            
            from novel_agent.services.manuscript_workspace import read_chapter_plain_text

            text = read_chapter_plain_text(self.root_dir, prev_id).strip()
            if text:
                tail = text[-500:] if len(text) > 500 else text
                parts_info.append(f"【时序无缝衔接参考 | 第 {prev_id} 章结尾段落】\n{tail}\n（请在此段落基础上，进行无缝的时序与剧情延续，保持笔触和镜头连贯）")

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
        query_parts = [chapter_goal]
        query_parts.extend(scene.get("must_include", []))
        query_parts.extend(scene.get("characters", []))
        query_parts.extend(scene.get("objects", []))
        query_parts.extend(scene.get("threads", []))
        query = " ".join(str(p) for p in query_parts if str(p).strip())
        if not query:
            return "- 暂无"

        from novel_agent.control.long_run import resolve_vector_search_window

        current_chapter = str(scene.get("chapter_id", "")).split("-")[0] or None
        window = resolve_vector_search_window(self.root_dir)

        results = self.vector_store.search(
            query=query,
            top_k=8,
            filters={"type": "event"},
            near_chapter_id=current_chapter,
            chapter_window=window,
        )

        lines = []
        seen = set()
        for r in results:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            meta = r.get("metadata", {})
            chapter = meta.get("chapter", "?")
            lines.append(f"- 第 {chapter} 章 / {r['id']}：{r['text']}")

        return "\n".join(lines) if lines else "- 暂无"

    def _relevant_timeline(self, chapter_goal: str, scene: Dict[str, Any]) -> str:
        query_parts = [chapter_goal]
        query_parts.extend(scene.get("must_include", []))
        query_parts.extend(scene.get("characters", []))
        query_parts.extend(scene.get("objects", []))
        query_parts.extend(scene.get("threads", []))
        query = " ".join(str(p) for p in query_parts if str(p).strip())
        if not query:
            return "- 暂无"

        from novel_agent.control.long_run import resolve_vector_search_window

        current_chapter = str(scene.get("chapter_id", "")).split("-")[0] or None
        window = resolve_vector_search_window(self.root_dir)

        results = self.vector_store.search(
            query=query,
            top_k=8,
            filters={"type": "timeline_node"},
            near_chapter_id=current_chapter,
            chapter_window=window,
        )

        lines = []
        seen = set()
        for r in results:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            meta = r.get("metadata", {})
            node_type = meta.get("node_type", "")
            lines.append(f"- 节点/{node_type}/{r['id']}：{r['text']}")

        return "\n".join(lines) if lines else "- 暂无"

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
