import json
import dataclasses
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.agents.asset_compressor import compress_assets
from novel_agent.agents.auditor import AuditorAgent
from novel_agent.agents.chapter_planner import ChapterPlannerAgent
from novel_agent.agents.chapter_summary import ChapterSummaryAgent
from novel_agent.agents.chief_editor import ChiefEditorAgent
from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.agents.continuity_checker import ContinuityCheckerAgent
from novel_agent.agents.length_fix import LengthFixAgent
from novel_agent.agents.managing_editor import ManagingEditorAgent
from novel_agent.agents.planner import PlannerAgent
from novel_agent.agents.state_extractor import StateExtractorAgent
from novel_agent.agents.stitch_editor import StitchEditorAgent
from novel_agent.agents.style_editor import StyleEditorAgent
from novel_agent.agents.writer import WriterAgent
from novel_agent.agents.persona_reader import PersonaReaderAgent
from novel_agent.approval import ApprovalGate
from novel_agent.control.calibration import build_calibration_report
from novel_agent.control.narrative_debt import classify_debt
from novel_agent.control.runtime_policy import (
    format_scale_profile_for_chief_editor,
    resolve_runtime_policy,
)
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.dashboard import write_dashboard
from novel_agent.logging_config import get_logger
from novel_agent.pipeline import PipelineConfig
from novel_agent.prompts import PromptRepository
from novel_agent.state.manager import StateManager
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.vector_store import VectorStore, create_vector_store
from novel_agent.services.chapter_postprocess import ChapterPostProcessor
from novel_agent.services.chapter_pipeline import ChapterPipelineRunner
from novel_agent.progress import (
    emit_progress,
    emit_complete,
    emit_error,
    emit_hook_warning,
    emit_log,
)

# 引入拆分出的 Phase 与 Context
from novel_agent.phases.base import ChapterContext
from novel_agent.phases.generation import GenerationPhase, _detect_truncation
from novel_agent.phases.audit import AuditPhase
from novel_agent.phases.post_audit import PostAuditPhase
from novel_agent.async_bridge import run_sync
from novel_agent.orchestrator_checkpoint import ChapterCheckpoint
from novel_agent.orchestrator_hooks import HookDispatcher
from novel_agent.orchestrator_batch import (
    chapter_pipeline_complete as batch_chapter_pipeline_complete,
    maybe_pause_after_skip as batch_maybe_pause_after_skip,
    record_batch_retry_skip as batch_record_batch_retry_skip,
)
from novel_agent.orchestrator_novel_batch import (
    arun_arcs as novel_batch_arun_arcs,
    arun_novel as novel_batch_arun_novel,
    arun_novel_continue as novel_batch_arun_novel_continue,
    run_chapter_briefs as novel_batch_run_chapter_briefs,
)
from novel_agent.orchestrator_types import ChapterResult

logger = get_logger("orchestrator")

_COMPRESS_EVERY_N_CHAPTERS = 10
_COMPRESS_EVENT_THRESHOLD = 100


def _read_text_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


class NovelOrchestrator:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.root_dir = Path(config.root_dir)
        self.prompts = PromptRepository(self.root_dir)
        self.logger = logger
        
        # 注册所有 Agent
        self._init_agents(config)
        
        self.state_manager = StateManager(self.root_dir)
        self.approval_gate = ApprovalGate(interactive=config.interactive, plugin_manager=config.plugin_manager)
        self.vector_store: VectorStore = create_vector_store(
            config.embedding_config, self.root_dir
        )
        self.context_builder = ContextBuilderAgent(self.root_dir, self.vector_store)
        self.store = SQLiteStateStore(self.root_dir)
        self.prompts.store = self.store
        self._round_tokens_acc = 0
        
        # 挂载项目目录和存储库到大纲规划器及场景写入器 Agent
        if hasattr(self, "chapter_planner"):
            self.chapter_planner.project_dir = self.root_dir
            self.chapter_planner.store = self.store
        if hasattr(self, "writer"):
            self.writer.project_dir = self.root_dir
            self.writer.store = self.store

        # 实例化拆分出的具体 Phase 阶段类
        self.generation_phase = GenerationPhase(self)
        self.audit_phase = AuditPhase(self)
        self.post_audit_phase = PostAuditPhase(self)

        self.phases = [
            ("generation", self.generation_phase),
            ("audit", self.audit_phase),
            ("post_audit", self.post_audit_phase),
        ]
        if config.plugin_manager:
            for phase_plugin in config.plugin_manager.get_pipeline_phases():
                insert_after = phase_plugin.get_insert_after()
                self._insert_phase(phase_plugin.get_meta().name, phase_plugin, insert_after)

        self.chapter_post = ChapterPostProcessor(self)
        self._checkpoint = ChapterCheckpoint()
        self._hooks = HookDispatcher(self.root_dir)

    def _insert_phase(self, name: str, instance: Any, insert_after: Optional[str]) -> None:
        if not insert_after:
            self.phases.append((name, instance))
            return
        for idx, (pname, _) in enumerate(self.phases):
            if pname == insert_after:
                self.phases.insert(idx + 1, (name, instance))
                return
        self.phases.append((name, instance))

    def _init_agents(self, config: PipelineConfig) -> None:
        """Initialize all workflow agents."""
        overrides = {}
        if config.plugin_manager:
            overrides = config.plugin_manager.get_agent_overrides()

        factories = {
            "chief_editor": lambda: ChiefEditorAgent(config.get_llm("chief_editor"), self.prompts),
            "managing_editor": lambda: ManagingEditorAgent(config.get_llm("managing_editor"), self.prompts),
            "chapter_planner": lambda: ChapterPlannerAgent(config.get_llm("chapter_planner"), self.prompts),
            "planner": lambda: PlannerAgent(config.get_llm("planner"), self.prompts),
            "writer": lambda: WriterAgent(config.get_llm("writer"), self.prompts),
            "length_fix": lambda: LengthFixAgent(config.get_llm("length_fix"), self.prompts),
            "stitch_editor": lambda: StitchEditorAgent(config.get_llm("stitch_editor"), self.prompts),
            "style_editor": lambda: StyleEditorAgent(config.get_llm("style_editor"), self.prompts),
            "auditor": lambda: AuditorAgent(config.get_llm("auditor"), self.prompts),
            "state_extractor": lambda: StateExtractorAgent(config.get_llm("state_extractor"), self.prompts),
            "chapter_summary": lambda: ChapterSummaryAgent(config.get_llm("chapter_summary"), self.prompts),
            "continuity_checker": lambda: ContinuityCheckerAgent(config.get_llm("continuity_checker"), self.prompts),
            "persona_reader": lambda: PersonaReaderAgent(config.get_llm("persona_reader"), self.prompts, self.root_dir),
        }

        for role, plugin in overrides.items():
            if role in factories:
                factories[role] = lambda r=role, p=plugin: p.create_agent(config.get_llm(r), self.prompts)

        self.chief_editor = factories["chief_editor"]()
        self.managing_editor = factories["managing_editor"]()
        self.chapter_planner = factories["chapter_planner"]()
        self.planner = factories["planner"]()
        self.writer = factories["writer"]()
        self.length_fix = factories["length_fix"]()
        self.stitch_editor = factories["stitch_editor"]()
        self.style_editor = factories["style_editor"]()
        self.auditor = factories["auditor"]()
        self.auditor.root_dir = self.root_dir
        self.state_extractor = factories["state_extractor"]()
        self.chapter_summary_agent = factories["chapter_summary"]()
        self.continuity_checker = factories["continuity_checker"]()
        self.persona_reader = factories["persona_reader"]()

    def _load_checkpoint(self, chapter_dir: Path) -> Dict[str, Any]:
        return self._checkpoint.load(chapter_dir)

    def _save_checkpoint(
        self,
        chapter_dir: Path,
        chapter_id: str,
        stage: str,
        completed: List[str],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._checkpoint.save(
            chapter_dir,
            chapter_id,
            stage,
            completed,
            self._write_json,
            extra=extra,
        )

    def _rollback_checkpoint_stages(
        self,
        chapter_dir: Path,
        chapter_id: str,
        completed: List[str],
        drop_stages: Tuple[str, ...],
        last_stage: str,
        progress_step: str,
        progress_status: str,
        progress_data: Optional[Dict[str, Any]] = None,
        checkpoint_extra: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        return self._checkpoint.rollback_stages(
            chapter_dir,
            chapter_id,
            completed,
            drop_stages,
            last_stage,
            progress_step,
            progress_status,
            self._write_json,
            progress_data=progress_data,
            checkpoint_extra=checkpoint_extra,
        )

    def _rollback_checkpoint_after_approval_rejection(
        self,
        chapter_dir: Path,
        chapter_id: str,
        completed: List[str],
    ) -> List[str]:
        """Drop audit/post_audit markers so a retry re-runs review and persistence."""
        return self._checkpoint.rollback_after_approval_rejection(
            chapter_dir, chapter_id, completed, self._write_json
        )

    @staticmethod
    def _load_checkpoint_data(path: Path) -> Dict[str, Any]:
        return ChapterCheckpoint.load_data(path)

    def _call_hook(self, hook_name: str, chapter_id: str, fn, default=None):
        return self._hooks.call(hook_name, chapter_id, fn, default)

    # ------------------------------------------------------------------
    # Multi-chapter orchestration
    # ------------------------------------------------------------------

    def run_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
    ) -> List[ChapterResult]:
        return run_sync(
            self.arun_novel(theme, genre, target_chapters, special_requirements)
        )

    def _record_batch_retry_skip(
        self,
        chapter_id: str,
        arc_id: str,
        *,
        reason: str,
        message: str,
        step: str,
    ) -> None:
        batch_record_batch_retry_skip(
            self.root_dir, chapter_id, arc_id, reason=reason, message=message, step=step
        )

    def _maybe_pause_after_skip(
        self,
        chapter_id: str,
        arc_id: str,
        consecutive_skips: int,
        skip_pause_max: int,
    ) -> bool:
        return batch_maybe_pause_after_skip(
            self.root_dir, chapter_id, arc_id, consecutive_skips, skip_pause_max
        )

    def _chapter_pipeline_complete(self, chapter_id: str) -> bool:
        return batch_chapter_pipeline_complete(self.root_dir, chapter_id)

    async def _run_chapter_briefs(
        self,
        chapter_briefs: List[Dict[str, Any]],
        arc_id: str = "",
        calibration_interval: int = 0,
        all_chapters_ref: Optional[List[Dict[str, Any]]] = None,
        global_offset: int = 0,
    ) -> Tuple[List[ChapterResult], bool]:
        return await novel_batch_run_chapter_briefs(
            self,
            chapter_briefs,
            arc_id=arc_id,
            calibration_interval=calibration_interval,
            all_chapters_ref=all_chapters_ref,
            global_offset=global_offset,
        )

    async def arun_arcs(
        self,
        arc_id: Optional[str] = None,
        arc_ids: Optional[List[str]] = None,
        start_arc_id: Optional[str] = None,
        resume: bool = True,
        max_chapters: Optional[int] = None,
    ) -> List[ChapterResult]:
        return await novel_batch_arun_arcs(
            self,
            arc_id=arc_id,
            arc_ids=arc_ids,
            start_arc_id=start_arc_id,
            resume=resume,
            max_chapters=max_chapters,
        )

    async def arun_novel_continue(
        self,
        resume: bool = True,
        max_chapters: Optional[int] = None,
        *,
        full_book: bool = False,
    ) -> List[ChapterResult]:
        return await novel_batch_arun_novel_continue(
            self,
            resume=resume,
            max_chapters=max_chapters,
            full_book=full_book,
        )

    async def arun_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
    ) -> List[ChapterResult]:
        return await novel_batch_arun_novel(
            self,
            theme,
            genre=genre,
            target_chapters=target_chapters,
            special_requirements=special_requirements,
        )

    def _auto_compress_assets(self, threshold: Optional[int] = None) -> None:
        try:
            from novel_agent.control.long_run import resolve_compress_schedule

            if threshold is None:
                _, _, threshold = resolve_compress_schedule(self.root_dir)
            state = self.state_manager.get_state()
            event_count = len(state.get("events", []))
            if event_count < (threshold or _COMPRESS_EVENT_THRESHOLD):
                return
            compress_assets(self.root_dir, self.config.get_llm("asset_compressor"), self.prompts)
        except Exception as exc:
            logger.warning("Auto asset compression failed: %s", exc)

    def _write_calibration_report(
        self,
        chapter_id: str,
        planned_chapters: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        try:
            outline_path = self.root_dir / "workspace" / "outline.json"
            outline = self._load_checkpoint_data(outline_path)
            chapters = planned_chapters or self.store.get_chapters()
            debt = {
                "foreshadows": classify_debt(self.store.list_foreshadows(), chapter_id, default_period=10),
                "reader_promises": classify_debt(self.store.list_reader_promises(), chapter_id, default_period=3),
                "secrets": classify_debt(self.store.list_secrets(), chapter_id, default_period=15),
            }
            report = build_calibration_report(outline, chapters, debt)
            self._write_json(
                self.root_dir / "workspace" / "reports" / f"calibration_chapter_{chapter_id}.json",
                report,
            )
        except Exception as exc:
            logger.warning("Calibration report failed for chapter %s: %s", chapter_id, exc)

    # ------------------------------------------------------------------
    # Single-chapter pipeline
    # ------------------------------------------------------------------

    def run_chapter(self, chapter_id: str, chapter_goal: str) -> ChapterResult:
        from novel_agent.async_bridge import run_sync

        return run_sync(self.arun_chapter(chapter_id, chapter_goal))

    async def arun_chapter(self, chapter_id: str, chapter_goal: str) -> ChapterResult:
        logger.info("Starting chapter %s generation (Async)", chapter_id)
        self._estimate_and_budget_chapter(chapter_id)
        emit_progress("init", "running", chapter_id=chapter_id)
        self._ensure_project_dirs()
        emit_progress("init", "done", chapter_id=chapter_id)
        return await ChapterPipelineRunner(self).run(chapter_id, chapter_goal)

    async def arun_gate_only(self, chapter_id: str) -> ChapterResult:
        from novel_agent.services.chapter_gate_rerun import run_gate_only_rerun

        logger.info("Gate-only rerun for chapter %s", chapter_id)
        self._ensure_project_dirs()
        return await run_gate_only_rerun(self, chapter_id)

    def _emit_chapter_complete_hooks(
        self,
        chapter_id: str,
        ctx: ChapterContext,
        result: ChapterResult,
        word_count: int,
    ) -> None:
        if not self.config.plugin_manager:
            return
        chapter_dir = ctx.chapter_dir
        self.config.plugin_manager.event_bus.publish(
            "chapter.completed",
            {
                "chapter_id": chapter_id,
                "final_path": str(chapter_dir / "chapter_final.txt"),
                "word_count": word_count,
            },
        )
        for hook in self.config.plugin_manager.get_hooks():
            try:
                hook.on_chapter_complete(ctx, result)
            except Exception as e:
                self._on_hook_error("on_chapter_complete", e, chapter_id)

    def _ensure_project_dirs(self) -> None:
        for relative in [
            "assets",
            "state",
            "prompts",
            "workspace/chapters",
            "dashboard",
            "state/snapshots",
        ]:
            (self.root_dir / relative).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _estimate_and_budget_chapter(self, chapter_id: str) -> None:
        try:
            from novel_agent.services.budget import estimate_and_budget_chapter_logic
            avg_in, avg_out = self.store.get_average_cost_per_scene()
            max_tokens = getattr(self.config, "max_tokens_per_chapter", 0)
            
            _, skip_style_edit = estimate_and_budget_chapter_logic(
                chapter_id=chapter_id,
                root_dir=self.root_dir,
                avg_in=avg_in,
                avg_out=avg_out,
                max_tokens_per_chapter=max_tokens
            )
            self.config.skip_style_edit = skip_style_edit
        except Exception as e:
            logger.warning("Failed to estimate chapter cost: %s", e)

    def _clear_call_logs(self) -> None:
        for client in self.config.llm_registry.values():
            if hasattr(client, "call_log"):
                client.call_log.clear()
        if hasattr(self.config.llm, "call_log"):
            self.config.llm.call_log.clear()

    def reset_round_token_accumulator(self) -> None:
        """Start a fresh autopilot round: drop stale call_log from failed chapters."""
        self._round_tokens_acc = 0
        self._clear_call_logs()

    def consume_round_tokens(self) -> int:
        used = int(getattr(self, "_round_tokens_acc", 0) or 0)
        self._round_tokens_acc = 0
        return used

    def _persist_llm_cost(self, chapter_id: str) -> None:
        try:
            from novel_agent.pricing import resolve_model_prices_usd

            logs = self.config.get_call_log()
            round_tokens = 0
            for log in logs:
                round_tokens += int(
                    log.get("total_tokens")
                    or (log.get("prompt_tokens", 0) + log.get("completion_tokens", 0))
                    or 0
                )
            self._round_tokens_acc = int(getattr(self, "_round_tokens_acc", 0) or 0) + round_tokens
            for log in logs:
                model_name = log.get("model", "")
                prompt_tokens = log.get("prompt_tokens", 0)
                completion_tokens = log.get("completion_tokens", 0)
                in_price, out_price = resolve_model_prices_usd(model_name)
                input_cost = (prompt_tokens / 1000) * in_price
                output_cost = (completion_tokens / 1000) * out_price
                
                import uuid
                call_id = f"call_{uuid.uuid4().hex[:8]}"
                self.store.log_llm_cost(
                    call_id=call_id,
                    model=model_name,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    project_id=str(self.root_dir.name)
                )
            
            self._clear_call_logs()
            logger.info("Successfully persisted and cleared %d LLM cost logs for chapter %s", len(logs), chapter_id)
        except Exception as e:
            logger.warning("Failed to persist LLM cost logs: %s", e)
