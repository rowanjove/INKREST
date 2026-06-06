"""Single-chapter pipeline: planning, phased execution, finalize."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from novel_agent.control.runtime_policy import (
    format_runtime_context_for_planner,
    resolve_runtime_policy,
)
from novel_agent.dashboard import write_dashboard
from novel_agent.logging_config import get_logger
from novel_agent.phases.base import ChapterContext
from novel_agent.progress import emit_complete, emit_progress
from novel_agent.services.pipeline_trace import append_trace_event

if TYPE_CHECKING:
    from novel_agent.orchestrator import ChapterResult, NovelOrchestrator

logger = get_logger("services.chapter_pipeline")


def _read_text_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


class ChapterPipelineRunner:
    """Runs plan → phases → vector index → dashboard for one chapter."""

    def __init__(self, orchestrator: "NovelOrchestrator") -> None:
        self._o = orchestrator

    async def run(self, chapter_id: str, chapter_goal: str) -> "ChapterResult":
        from novel_agent.orchestrator import ChapterResult

        chapter_dir = self._o.root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
        scenes_dir = chapter_dir / "scenes"
        reports_dir = chapter_dir / "reports"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = self._o._load_checkpoint(chapter_dir)
        completed: List[str] = list(checkpoint.get("completed_stages", []))
        if completed:
            logger.info(
                "Resuming chapter %s from checkpoint, completed stages: %s",
                chapter_id,
                completed,
            )

        ctx, plan = await self._run_planning(
            chapter_id, chapter_goal, chapter_dir, scenes_dir, reports_dir
        )

        early, ctx = await self._run_phases(
            chapter_id, chapter_dir, reports_dir, completed, ctx
        )
        if early is not None:
            return early

        await self._o.chapter_post.index_chapter_vectors(
            chapter_id,
            plan,
            ctx.final_text or "",
            ctx.chapter_summary or "",
            ctx.extracted_state or {},
        )

        write_dashboard(self._o.root_dir)

        logger.info("Chapter %s completed successfully", chapter_id)
        try:
            from novel_agent.services.progress_sync import record_chapter_success

            record_chapter_success(self._o.root_dir, chapter_id, pipeline_complete=True)
        except Exception:
            pass
        wc_count = ctx.wordcount["count"] if ctx.wordcount else 0
        risk_level = ctx.audit.get("risk_level", "") if ctx.audit else ""
        emit_complete(chapter_id, {"word_count": wc_count, "risk_level": risk_level})
        self._o._persist_llm_cost(chapter_id)

        result = ChapterResult(
            chapter_id=chapter_id,
            final_path=chapter_dir / "chapter_final.txt",
            audit=ctx.audit or {},
            warnings=list(ctx.warnings),
        )
        self._o._emit_chapter_complete_hooks(chapter_id, ctx, result, wc_count)

        policy = resolve_runtime_policy(self._o.root_dir)
        if policy.calibration_interval > 0:
            try:
                if int(chapter_id) % policy.calibration_interval == 0:
                    self._o._write_calibration_report(chapter_id)
            except ValueError:
                pass

        return result

    async def _run_planning(
        self,
        chapter_id: str,
        chapter_goal: str,
        chapter_dir: Path,
        scenes_dir: Path,
        reports_dir: Path,
    ) -> tuple[ChapterContext, Dict[str, Any]]:
        logger.info("Step 1: Planning chapter %s (Async)", chapter_id)
        emit_progress("planner", "running", chapter_id=chapter_id)

        from novel_agent.control.runtime_policy import (
            goal_fingerprint,
            plan_fingerprint,
            should_skip_chapter_planner,
        )

        checkpoint = self._o._load_checkpoint(chapter_dir)
        completed_stages = list(checkpoint.get("completed_stages") or [])
        goal_fp = goal_fingerprint(chapter_goal)
        if checkpoint.get("goal_hash") and checkpoint["goal_hash"] != goal_fp:
            logger.warning(
                "Chapter %s goal changed; clearing checkpoint stages for replan",
                chapter_id,
            )
            from novel_agent.services.report_validity import invalidate_chapter_reports

            invalidate_chapter_reports(
                reports_dir,
                reason="goal_hash_mismatch",
                goal_hash=goal_fp,
            )
            completed_stages = []
            self._o._save_checkpoint(
                chapter_dir,
                chapter_id,
                "goal_changed",
                [],
                extra={"goal_hash": goal_fp, "resumable_from": "planner"},
            )

        plan_path = chapter_dir / "plan.json"
        if plan_path.exists() and checkpoint.get("goal_hash") == goal_fp:
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                plan = {}
            skip, skip_reason = should_skip_chapter_planner(
                checkpoint, completed_stages, goal_fp, plan
            )
            if skip and plan:
                ctx = ChapterContext(
                    chapter_id=chapter_id,
                    chapter_goal=chapter_goal,
                    chapter_dir=chapter_dir,
                    scenes_dir=scenes_dir,
                    reports_dir=reports_dir,
                    plan=plan,
                )
                emit_progress(
                    "planner",
                    "skipped",
                    {"reason": skip_reason, "plan_hash": checkpoint.get("plan_hash")},
                    chapter_id,
                )
                return ctx, plan

        quality_rewrite_hints = ""
        quality_path = reports_dir / "quality.json"
        if quality_path.exists():
            try:
                quality_doc = json.loads(quality_path.read_text(encoding="utf-8"))
                quality_rewrite_hints = str(quality_doc.get("rewrite_hints") or "")
            except (json.JSONDecodeError, OSError):
                pass

        hints = self._o.chapter_post.gather_planner_hints(chapter_id, chapter_goal)

        ctx = ChapterContext(
            chapter_id=chapter_id,
            chapter_goal=chapter_goal,
            chapter_dir=chapter_dir,
            scenes_dir=scenes_dir,
            reports_dir=reports_dir,
            plan={},
        )

        if self._o.config.plugin_manager:
            for hook in self._o.config.plugin_manager.get_hooks():
                ctx = self._o._call_hook(
                    "before_planning",
                    chapter_id,
                    lambda h=hook, c=ctx: h.before_planning(c),
                    default=ctx,
                )

        runtime_policy = resolve_runtime_policy(self._o.root_dir)
        runtime_context = format_runtime_context_for_planner(runtime_policy)
        from novel_agent.services.continuity_pack import build_planner_continuity_block

        continuity_context = build_planner_continuity_block(
            self._o.root_dir, chapter_id, chapter_goal
        )
        planner = self._o.planner
        plan_kwargs = {
            "duplicate_warnings": hints.duplicate_warnings or None,
            "foreshadow_recommendations": hints.foreshadow_recommendations or None,
            "runtime_context": runtime_context,
            "quality_rewrite_hints": quality_rewrite_hints or None,
            "max_plan_scenes": runtime_policy.max_plan_scenes,
            "continuity_context": continuity_context or None,
            "root_dir": self._o.root_dir,
        }
        if hasattr(planner, "acreate_plan"):
            plan = await planner.acreate_plan(chapter_id, ctx.chapter_goal, **plan_kwargs)
        else:
            plan = planner.create_plan(chapter_id, ctx.chapter_goal, **plan_kwargs)

        if self._o.config.plugin_manager:
            for hook in self._o.config.plugin_manager.get_hooks():
                plan = self._o._call_hook(
                    "after_planning",
                    chapter_id,
                    lambda h=hook, p=plan: h.after_planning(ctx, p),
                    default=plan,
                )

        self._o._write_json(chapter_dir / "plan.json", plan)
        ctx = dataclasses.replace(ctx, plan=plan)
        self._o._save_checkpoint(
            chapter_dir,
            chapter_id,
            "planner",
            completed_stages,
            extra={
                "goal_hash": goal_fp,
                "plan_hash": plan_fingerprint(plan),
                "resumable_from": "generation",
            },
        )
        emit_progress("planner", "done", {"scenes": len(plan.get("scenes", []))}, chapter_id)
        return ctx, plan

    async def _run_phases(
        self,
        chapter_id: str,
        chapter_dir: Path,
        reports_dir: Path,
        completed: List[str],
        ctx: ChapterContext,
    ) -> tuple[Optional["ChapterResult"], ChapterContext]:
        from novel_agent.control.long_run import should_merge_review_stages

        merge_review = should_merge_review_stages(self._o.root_dir)
        phase_list = [
            (n, p)
            for n, p in self._o.phases
            if not (merge_review and n == "post_audit")
        ]
        phase_by_name = dict(self._o.phases)

        if (
            merge_review
            and "audit" in completed
            and "post_audit" not in completed
            and "post_audit" in phase_by_name
        ):
            early, ctx = await self._execute_phase(
                "post_audit",
                phase_by_name["post_audit"],
                chapter_id,
                chapter_dir,
                reports_dir,
                completed,
                ctx,
            )
            if early is not None:
                return early, ctx
            completed.append("post_audit")
            self._o._save_checkpoint(chapter_dir, chapter_id, "post_audit", completed)

        for name, phase in phase_list:
            if name in completed:
                restored = self._restore_skipped_phase_ctx(
                    name, chapter_dir, reports_dir, completed, ctx
                )
                if restored is None:
                    continue
                ctx = restored
                continue

            early, ctx = await self._execute_phase(
                name, phase, chapter_id, chapter_dir, reports_dir, completed, ctx
            )
            if early is not None:
                return early, ctx

            completed.append(name)
            self._o._save_checkpoint(chapter_dir, chapter_id, name, completed)

            if merge_review and name == "audit":
                post_phase = dict(self._o.phases).get("post_audit")
                if post_phase and "post_audit" not in completed:
                    early2, ctx = await self._execute_phase(
                        "post_audit",
                        post_phase,
                        chapter_id,
                        chapter_dir,
                        reports_dir,
                        completed,
                        ctx,
                    )
                    if early2 is not None:
                        return early2, ctx
                    completed.append("post_audit")
                    self._o._save_checkpoint(chapter_dir, chapter_id, "post_audit", completed)

        return None, ctx

    def _restore_skipped_phase_ctx(
        self,
        name: str,
        chapter_dir: Path,
        reports_dir: Path,
        completed: List[str],
        ctx: ChapterContext,
    ) -> Optional[ChapterContext]:
        logger.info("Checkpoint: skipping stage %s (already complete)", name)
        if name == "generation":
            final_text = _read_text_safe(chapter_dir / "chapter_final.txt")
            if not final_text:
                logger.warning(
                    "Checkpoint says generation complete but chapter_final.txt is empty, re-running"
                )
                completed.remove("generation")
                return None
            return dataclasses.replace(ctx, final_text=final_text)
        if name == "audit":
            audit_data = self._o._load_checkpoint_data(reports_dir / "audit.json")
            summary_data = _read_text_safe(chapter_dir / "chapter_summary.md")
            wc_data = self._o._load_checkpoint_data(reports_dir / "wordcount.json")
            ext_state = self._o._load_checkpoint_data(chapter_dir / "state_update.json")
            return dataclasses.replace(
                ctx,
                audit=audit_data,
                chapter_summary=summary_data,
                wordcount=wc_data,
                extracted_state=ext_state,
            )
        return ctx

    async def _execute_phase(
        self,
        name: str,
        phase: Any,
        chapter_id: str,
        chapter_dir: Path,
        reports_dir: Path,
        completed: List[str],
        ctx: ChapterContext,
    ) -> tuple[Optional["ChapterResult"], ChapterContext]:
        from novel_agent.orchestrator import ChapterResult
        import time

        t0 = time.perf_counter()
        emit_progress(name, "running", chapter_id=chapter_id)
        append_trace_event(chapter_dir, step=name, status="running", chapter_id=chapter_id)

        def _finish_phase(status: str = "done") -> None:
            elapsed = (time.perf_counter() - t0) * 1000
            emit_progress(name, status, chapter_id=chapter_id)
            append_trace_event(
                chapter_dir,
                step=name,
                status=status,
                chapter_id=chapter_id,
                duration_ms=elapsed,
            )

        if name == "generation":
            if hasattr(phase, "aexecute"):
                ctx = await phase.aexecute(ctx)
            else:
                ctx = phase.execute(ctx)
            _finish_phase("done")
            return None, ctx

        if name == "audit":
            early, ctx = await self._execute_audit_phase(
                phase, chapter_id, chapter_dir, reports_dir, completed, ctx
            )
            _finish_phase("blocked" if early is not None else "done")
            return early, ctx

        if name == "post_audit":
            if hasattr(phase, "aexecute"):
                ctx, approved = await phase.aexecute(ctx)
            else:
                ctx, approved = phase.execute(ctx)
            if not approved:
                rolled = self._o._rollback_checkpoint_after_approval_rejection(
                    chapter_dir, chapter_id, completed
                )
                completed[:] = rolled
                rejection_warning = "章节未通过审批，已回滚检查点以便重试审校与落库。"
                _finish_phase("blocked")
                return (
                    ChapterResult(
                        chapter_id=chapter_id,
                        final_path=chapter_dir / "chapter_final.txt",
                        audit={"risk_level": "pending", "issues": ["未通过审批"], "state_update": {}},
                        warnings=list(ctx.warnings) + [rejection_warning],
                    ),
                    ctx,
                )
            _finish_phase("done")
            return None, ctx

        if hasattr(phase, "aexecute"):
            ctx = await phase.aexecute(ctx)
        else:
            ctx = phase.execute(ctx)
        _finish_phase("done")
        return None, ctx

    async def _execute_audit_phase(
        self,
        phase: Any,
        chapter_id: str,
        chapter_dir: Path,
        reports_dir: Path,
        completed: List[str],
        ctx: ChapterContext,
    ) -> tuple[Optional["ChapterResult"], ChapterContext]:
        from novel_agent.orchestrator import ChapterResult

        if self._o.config.plugin_manager:
            for hook in self._o.config.plugin_manager.get_hooks():
                ctx = self._o._call_hook(
                    "before_audit",
                    chapter_id,
                    lambda h=hook, c=ctx: h.before_audit(c),
                    default=ctx,
                )

        (chapter_dir / "chapter_final.txt").write_text(ctx.final_text or "", encoding="utf-8")
        if hasattr(phase, "aexecute"):
            ctx = await phase.aexecute(ctx)
        else:
            ctx = phase.execute(ctx)

        if self._o.config.plugin_manager:
            for hook in self._o.config.plugin_manager.get_hooks():
                ctx = self._o._call_hook(
                    "after_audit",
                    chapter_id,
                    lambda h=hook, c=ctx: h.after_audit(c, c.audit),
                    default=ctx,
                )

        from novel_agent.services.unified_gate import run_unified_review_gate

        gate = await run_unified_review_gate(
            self._o, chapter_id, ctx, reports_dir, chapter_dir
        )
        ctx = gate.ctx
        if gate.blocked:
            from novel_agent.control.runtime_policy import goal_fingerprint

            rolled = self._o._rollback_checkpoint_stages(
                chapter_dir,
                chapter_id,
                completed,
                drop_stages=("audit", "post_audit"),
                last_stage="quality_blocked",
                progress_step="unified_gate",
                progress_status="blocked",
                progress_data={
                    "resumable_from": "audit",
                    "mode": gate.quality_report.get("mode"),
                },
                checkpoint_extra={"goal_hash": goal_fingerprint(ctx.chapter_goal)},
            )
            completed[:] = rolled
            return (
                ChapterResult(
                    chapter_id=chapter_id,
                    final_path=chapter_dir / "chapter_final.txt",
                    audit=ctx.audit or {},
                    warnings=list(ctx.warnings) + [gate.block_message],
                ),
                ctx,
            )
        return None, ctx