"""Chapter planning hints, vector indexing, and quality reporting."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from novel_agent.control.narrative_debt import classify_debt
from novel_agent.control.scale_profile import is_vector_enabled_for_project
from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.quality_rewrite import build_quality_rewrite_hints
from novel_agent.quality.settings import (
    format_quality_block_message,
    quality_gate_blocks,
    resolve_persona_evaluations,
    resolve_quality_mode,
    should_run_persona_evaluations,
)
from novel_agent.state.vector_store import VectorChunk

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator

logger = get_logger("services.chapter_postprocess")


@dataclass
class PlannerHints:
    duplicate_warnings: str = ""
    foreshadow_recommendations: str = ""


@dataclass
class QualityReportOutcome:
    report: Dict[str, Any]
    blocked: bool = False
    block_message: str = ""


class ChapterPostProcessor:
    """Post-audit helpers extracted from NovelOrchestrator."""

    def __init__(self, orchestrator: "NovelOrchestrator") -> None:
        self._o = orchestrator

    def vector_enabled(self) -> bool:
        return is_vector_enabled_for_project(self._o.root_dir)

    def gather_planner_hints(self, chapter_id: str, chapter_goal: str) -> PlannerHints:
        from novel_agent.control.runtime_policy import resolve_runtime_policy

        policy = resolve_runtime_policy(self._o.root_dir)
        duplicate = self._query_duplicate_warnings(chapter_id, chapter_goal)
        if not policy.semantic_search_effective:
            stub_note = (
                "【系统】语义向量未生效（stub/未配置 API）：跨章剧情去重与向量伏笔召回已跳过。"
            )
            duplicate = f"{stub_note}\n{duplicate}".strip() if duplicate else stub_note
        foreshadow = self._query_foreshadow_recommendations(chapter_id, chapter_goal)
        overdue = self._query_overdue_debts(chapter_id)
        if overdue:
            foreshadow = f"{overdue}\n{foreshadow}" if foreshadow else overdue
        return PlannerHints(
            duplicate_warnings=duplicate,
            foreshadow_recommendations=foreshadow,
        )

    async def index_chapter_vectors(
        self,
        chapter_id: str,
        plan: Dict[str, Any],
        final_text: str,
        chapter_summary: str,
        extracted_state: Dict[str, Any],
    ) -> None:
        if not self.vector_enabled():
            emit_progress(
                "vector_index",
                "skipped",
                {"reason": "vector_disabled"},
                chapter_id,
            )
            return

        emit_progress("vector_index", "running", chapter_id=chapter_id)
        db_res = self._index_to_vector_store(
            chapter_id, plan, final_text, chapter_summary, extracted_state
        )
        if asyncio.isfuture(db_res) or asyncio.iscoroutine(db_res):
            await db_res
        emit_progress("vector_index", "done", chapter_id=chapter_id)

    async def write_quality_report(
        self,
        chapter_id: str,
        final_text: str,
        reports_dir: Path,
    ) -> QualityReportOutcome:
        logger.info("Building quality report for chapter %s", chapter_id)
        previous_text = self._previous_chapter_text(chapter_id)
        guards = None
        if self._o.config.plugin_manager:
            guards = self._o.config.plugin_manager.get_quality_guards()

        mode = resolve_quality_mode(self._o.root_dir)
        from novel_agent.quality.style_precheck import load_style_precheck_cache

        style_precheck = load_style_precheck_cache(reports_dir, final_text)
        quality_report = build_quality_report(
            final_text,
            previous_text,
            plugin_guards=guards,
            root_dir=self._o.root_dir,
            mode=mode,
            style_precheck=style_precheck,
        )
        rewrite_hints = build_quality_rewrite_hints(quality_report)
        if rewrite_hints.strip():
            quality_report["rewrite_hints"] = rewrite_hints

        persona_mode = resolve_persona_evaluations(self._o.root_dir)
        quality_report["persona_eval_mode"] = persona_mode
        if not should_run_persona_evaluations(self._o.root_dir, quality_report):
            quality_report["reader_evaluations"] = {}
        else:
            try:
                eval_tasks = [
                    self._o.persona_reader.aevaluate(final_text, chapter_id, "fan"),
                    self._o.persona_reader.aevaluate(final_text, chapter_id, "critic"),
                    self._o.persona_reader.aevaluate(final_text, chapter_id, "romance"),
                ]
                eval_results = await asyncio.gather(*eval_tasks)
                quality_report["reader_evaluations"] = {
                    "fan": eval_results[0],
                    "critic": eval_results[1],
                    "romance": eval_results[2],
                }
            except Exception as exc:
                logger.error("Failed to run reader persona evaluations: %s", exc)
                quality_report["reader_evaluations"] = {
                    "fan": self._o.persona_reader._empty_evaluation("fan"),
                    "critic": self._o.persona_reader._empty_evaluation("critic"),
                    "romance": self._o.persona_reader._empty_evaluation("romance"),
                }

        self._o._write_json(reports_dir / "quality.json", quality_report)
        blocked = quality_gate_blocks(quality_report, mode)
        progress_status = "blocked" if blocked else "done"
        emit_progress(
            "quality_guard",
            progress_status,
            {
                "mode": mode,
                "overall_pass": quality_report.get("overall_pass"),
                "overall_status": (quality_report.get("guard_summary") or {}).get("overall_status"),
            },
            chapter_id,
        )
        block_message = format_quality_block_message(quality_report) if blocked else ""
        return QualityReportOutcome(
            report=quality_report,
            blocked=blocked,
            block_message=block_message,
        )

    def _query_duplicate_warnings(self, chapter_id: str, chapter_goal: str) -> str:
        if not self.vector_enabled():
            return ""
        duplicate_warnings = ""
        try:
            from novel_agent.control.long_run import resolve_vector_search_window

            window = resolve_vector_search_window(self._o.root_dir)
            similar_summaries = self._o.vector_store.search(
                query=chapter_goal,
                top_k=5,
                filters={"type": "chapter_summary"},
                near_chapter_id=chapter_id,
                chapter_window=window,
            )
            is_stub = (not getattr(self._o.vector_store, "api_key", "")) or (
                getattr(self._o.vector_store, "provider", "stub") == "stub"
            )
            if is_stub:
                return duplicate_warnings
            threshold = 0.75
            warning_lines = []
            for r in similar_summaries:
                score = r.get("score", 0.0)
                if score >= threshold:
                    ch_id = r.get("metadata", {}).get("chapter", "")
                    if str(ch_id) == str(chapter_id):
                        continue
                    text_snippet = r.get("text", "")[:150]
                    warning_lines.append(
                        f"- 第 {ch_id} 章 (相似度: {score:.2f}) 剧情摘要：{text_snippet}..."
                    )
            if warning_lines:
                duplicate_warnings = "\n".join(warning_lines)
                logger.warning(
                    "Chapter %s has high similarity plot warnings: %s",
                    chapter_id,
                    duplicate_warnings,
                )
        except Exception as e:
            logger.warning("Failed to query duplicate plot warnings: %s", e)
        return duplicate_warnings

    def _query_foreshadow_recommendations(self, chapter_id: str, chapter_goal: str) -> str:
        if not self.vector_enabled():
            return ""
        foreshadow_recommendations = ""
        try:
            from novel_agent.control.long_run import resolve_vector_search_window

            window = resolve_vector_search_window(self._o.root_dir)
            open_foreshadows = self._o.vector_store.search(
                query=chapter_goal,
                top_k=3,
                filters={"type": "foreshadow", "status": "open"},
                near_chapter_id=chapter_id,
                chapter_window=window,
            )
            recommend_lines = []
            for r in open_foreshadows:
                meta = r.get("metadata", {})
                ch_id = meta.get("chapter", "")
                recommend_lines.append(
                    f"- 伏笔 ID: {r['id']} (来自第 {ch_id} 章) | 标题: {meta.get('title', '')} | 伏笔细节: {r['text']}"
                )
            if recommend_lines:
                foreshadow_recommendations = "\n".join(recommend_lines)
                logger.info(
                    "Found relevant open foreshadows for chapter %s: %s",
                    chapter_id,
                    foreshadow_recommendations,
                )
        except Exception as e:
            logger.warning("Failed to query open foreshadow recommendations: %s", e)
        return foreshadow_recommendations

    def _query_overdue_debts(self, chapter_id: str) -> str:
        recommend_lines = []
        try:
            foreshadows = classify_debt(
                self._o.store.list_foreshadows(), chapter_id, default_period=10
            )
            promises = classify_debt(
                self._o.store.list_reader_promises(), chapter_id, default_period=3
            )
            secrets = classify_debt(
                self._o.store.list_secrets(), chapter_id, default_period=15
            )

            all_debts = []
            for item in foreshadows:
                if item.get("status") == "open" and item.get("debt_status") in (
                    "overdue",
                    "due_soon",
                ):
                    all_debts.append((item, "伏笔"))
            for item in promises:
                if item.get("status") == "open" and item.get("debt_status") in (
                    "overdue",
                    "due_soon",
                ):
                    all_debts.append((item, "读者期待"))
            for item in secrets:
                if item.get("status") == "hidden" and item.get("debt_status") in (
                    "overdue",
                    "due_soon",
                ):
                    all_debts.append((item, "未揭露秘密"))

            def get_sort_key(debt_tuple: Tuple[Dict[str, Any], str]) -> Tuple[int, int]:
                item = debt_tuple[0]
                user_prio = -int(item.get("user_priority") or 0)
                try:
                    deadline = int(item.get("deadline_chapter") or 999)
                except ValueError:
                    deadline = 999
                return (user_prio, deadline)

            all_debts.sort(key=get_sort_key)
            for debt, kind in all_debts[:2]:
                ch = debt.get("chapter_id")
                deadline = debt.get("deadline_chapter")
                user_prio = int(debt.get("user_priority") or 0)
                prio_tag = " (用户指定高优先级)" if user_prio > 0 else ""
                recommend_lines.append(
                    f"- 【{kind}】ID: {debt['id']}{prio_tag} (源自第 {ch} 章，截止第 {deadline} 章) | 标题: {debt['title']} | 详情: {debt['description']}"
                )
        except Exception as exc:
            logger.warning("Failed to query narrative debts from SQLite: %s", exc)
        return "\n".join(recommend_lines)

    def _previous_chapter_text(self, chapter_id: str) -> str:
        try:
            chapter_num = int(chapter_id)
            if chapter_num <= 1:
                return ""
            prev_id = f"{chapter_num - 1:03d}"
        except ValueError:
            return ""

        prev_path = (
            self._o.root_dir / "workspace" / "chapters" / f"chapter_{prev_id}" / "chapter_final.txt"
        )
        if not prev_path.exists():
            return ""
        try:
            return prev_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def _index_to_vector_store(
        self,
        chapter_id: str,
        plan: Dict[str, Any],
        final_text: str,
        chapter_summary: str,
        extracted_state: Dict[str, Any],
    ) -> Any:
        if not self.vector_enabled():
            return None
        chunks: list[VectorChunk] = []
        chunks.append(
            VectorChunk(
                id=f"chapter_{chapter_id}_summary",
                type="chapter_summary",
                text=chapter_summary,
                metadata={"chapter": chapter_id},
            )
        )

        paragraphs = [p.strip() for p in final_text.split("\n\n") if p.strip()]
        buffer = ""
        chunk_idx = 0
        for para in paragraphs:
            if len(buffer) + len(para) > 500 and buffer:
                chunks.append(
                    VectorChunk(
                        id=f"chapter_{chapter_id}_prose_{chunk_idx}",
                        type="prose_chunk",
                        text=buffer,
                        metadata={"chapter": chapter_id, "chunk_index": chunk_idx},
                    )
                )
                chunk_idx += 1
                buffer = para
            else:
                buffer = f"{buffer}\n\n{para}" if buffer else para
        if buffer:
            chunks.append(
                VectorChunk(
                    id=f"chapter_{chapter_id}_prose_{chunk_idx}",
                    type="prose_chunk",
                    text=buffer,
                    metadata={"chapter": chapter_id, "chunk_index": chunk_idx},
                )
            )

        for f in extracted_state.get("foreshadows", []):
            if isinstance(f, dict) and f.get("id"):
                chunks.append(
                    VectorChunk(
                        id=f.get("id"),
                        type="foreshadow",
                        text=f.get("description", f.get("title", "")),
                        metadata={
                            "chapter": chapter_id,
                            "title": f.get("title", ""),
                            "status": f.get("status", "open"),
                        },
                    )
                )

        for idx, cb in enumerate(extracted_state.get("character_behaviors", [])):
            if isinstance(cb, dict) and cb.get("character"):
                chunks.append(
                    VectorChunk(
                        id=f"chapter_{chapter_id}_char_behavior_{idx}",
                        type="character_behavior",
                        text=cb.get("behavior", ""),
                        metadata={
                            "chapter": chapter_id,
                            "character": cb.get("character"),
                            "context": cb.get("context", ""),
                        },
                    )
                )

        report_path = (
            self._o.root_dir
            / "workspace"
            / "chapters"
            / f"chapter_{chapter_id}"
            / "reports"
            / "vector_index.json"
        )
        try:
            db_res = self._o.vector_store.upsert(chunks)
            self._o._write_json(report_path, {"status": "indexed", "chunk_count": len(chunks)})
            return db_res
        except Exception as exc:
            logger.warning("Vector indexing failed: %s", exc)
            self._o._write_json(
                report_path,
                {"status": "failed", "chunk_count": len(chunks), "error": str(exc)},
            )
            return None