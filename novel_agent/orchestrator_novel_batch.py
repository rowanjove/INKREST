"""Multi-chapter and full-novel async orchestration (extracted from orchestrator)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from novel_agent.control.runtime_policy import (
    format_scale_profile_for_chief_editor,
    resolve_runtime_policy,
)
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.logging_config import get_logger
from novel_agent.orchestrator_types import ChapterResult
from novel_agent.progress import emit_error, emit_log, emit_progress

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator

logger = get_logger("orchestrator.novel_batch")

async def run_chapter_briefs(
    orch: "NovelOrchestrator",
    chapter_briefs: List[Dict[str, Any]],
    arc_id: str = "",
    calibration_interval: int = 0,
    all_chapters_ref: Optional[List[Dict[str, Any]]] = None,
    global_offset: int = 0,
) -> Tuple[List[ChapterResult], bool]:
    """Run expand+arun_chapter for each brief. Returns (results, circuit_breaker_stopped)."""
    from novel_agent.control.long_run import (
        chapter_run_is_failure,
        resolve_batch_fail_streak_max,
        resolve_batch_skip_pause_max,
        resolve_chapter_retry_max,
        resolve_compress_schedule,
        resolve_pause_on_quality_block,
    )
    from novel_agent.services.batch_retry_queue import get_chapter_attempt_count
    from novel_agent.control.runtime_policy import (
        format_runtime_context_for_planner,
        resolve_runtime_policy,
    )

    hot_every, warm_every, compress_threshold = resolve_compress_schedule(orch.root_dir)
    fail_streak_max = resolve_batch_fail_streak_max(orch.root_dir)
    skip_pause_max = resolve_batch_skip_pause_max(orch.root_dir)
    chapter_retry_max = resolve_chapter_retry_max(orch.root_dir)
    pause_on_quality_block = resolve_pause_on_quality_block(orch.root_dir)
    consecutive_failures = 0
    consecutive_skips = 0
    results: List[ChapterResult] = []
    chapter_runtime = format_runtime_context_for_planner(resolve_runtime_policy(orch.root_dir))

    for i, chapter_brief in enumerate(chapter_briefs):
        chapter_id = chapter_brief.get("chapter_id", f"{global_offset + i + 1:03d}")
        logger.info(
            "Processing chapter %d (id=%s) arc=%s",
            global_offset + i + 1,
            chapter_id,
            arc_id or "-",
        )

        emit_progress(
            "chapter_planner",
            "running",
            {"arc_id": arc_id} if arc_id else {},
            chapter_id,
        )
        from novel_agent.control.chapter_brief import (
            brief_fingerprint,
            should_skip_chapter_planner_expand,
        )

        chapter_dir = orch.root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
        prior_attempts = get_chapter_attempt_count(orch.root_dir, chapter_id)
        if prior_attempts >= chapter_retry_max:
            from novel_agent.services.arc_queue import record_novel_batch_paused

            msg = (
                f"第 {chapter_id} 章已连续失败 {prior_attempts} 次，"
                f"已达上限 {chapter_retry_max}，已暂停全书批量以免继续消耗 token。"
            )
            emit_log("error", msg, "run_chapter", chapter_id)
            record_novel_batch_paused(
                orch.root_dir,
                reason="chapter_retry_exhausted",
                last_chapter=chapter_id,
                arc_id=arc_id,
                streak=prior_attempts,
            )
            emit_progress(
                "novel_batch",
                "paused",
                {
                    "reason": "chapter_retry_exhausted",
                    "chapter_id": chapter_id,
                    "attempts": prior_attempts,
                    "max": chapter_retry_max,
                },
                chapter_id,
            )
            return results, True

        skip_expand, skip_reason, cached = should_skip_chapter_planner_expand(
            orch.root_dir, chapter_id, chapter_brief
        )
        if skip_expand and cached:
            expanded = cached
            emit_progress(
                "chapter_planner",
                "skipped",
                {"reason": skip_reason},
                chapter_id,
            )
        else:
            if hasattr(orch.chapter_planner, "aexpand"):
                expanded = await orch.chapter_planner.aexpand(
                    chapter_brief, runtime_context=chapter_runtime
                )
            else:
                expanded = orch.chapter_planner.expand(
                    chapter_brief, runtime_context=chapter_runtime
                )
            stable_title = str(
                chapter_brief.get("chapter_title")
                or chapter_brief.get("title")
                or ""
            )
            if stable_title:
                expanded["chapter_title"] = stable_title
            orch._write_json(chapter_dir / "expanded_plan.json", expanded)
            orch._write_json(
                chapter_dir / "expanded_plan.meta.json",
                {"brief_fp": brief_fingerprint(chapter_brief), "reason": "llm_expand"},
            )
            emit_progress("chapter_planner", "done", chapter_id=chapter_id)

        chapter_goal = expanded.get(
            "detailed_synopsis",
            chapter_brief.get("chapter_goal", chapter_brief.get("goal", "")),
        )

        try:
            result = await orch.arun_chapter(chapter_id, chapter_goal)
            results.append(result)
            if chapter_run_is_failure(result):
                consecutive_failures += 1
                consecutive_skips += 1
                orch._record_batch_retry_skip(
                    chapter_id,
                    arc_id,
                    reason="quality_or_gate_failure",
                    message="; ".join(str(w) for w in (result.warnings or [])[:3]),
                    step="unified_gate",
                )
                emit_log(
                    "warn",
                    f"第 {chapter_id} 章未过统一门禁，已记入待重试队列。",
                    "unified_gate",
                    chapter_id,
                )
                if pause_on_quality_block:
                    from novel_agent.services.arc_queue import record_novel_batch_paused

                    record_novel_batch_paused(
                        orch.root_dir,
                        reason="quality_blocked",
                        last_chapter=chapter_id,
                        arc_id=arc_id,
                        streak=consecutive_failures,
                    )
                    emit_progress(
                        "novel_batch",
                        "paused",
                        {
                            "reason": "quality_blocked",
                            "last_chapter": chapter_id,
                            "arc_id": arc_id,
                        },
                        chapter_id,
                    )
                    return results, True
                if consecutive_failures >= fail_streak_max:
                    from novel_agent.services.arc_queue import record_novel_batch_paused

                    record_novel_batch_paused(
                        orch.root_dir,
                        reason="circuit_breaker",
                        last_chapter=chapter_id,
                        arc_id=arc_id,
                        streak=consecutive_failures,
                    )
                    emit_progress(
                        "novel_batch",
                        "paused",
                        {
                            "reason": "circuit_breaker",
                            "streak": consecutive_failures,
                            "last_chapter": chapter_id,
                            "arc_id": arc_id,
                        },
                        chapter_id,
                    )
                    return results, True
                if orch._maybe_pause_after_skip(
                    chapter_id, arc_id, consecutive_skips, skip_pause_max
                ):
                    return results, True
            else:
                consecutive_failures = 0
                consecutive_skips = 0
                try:
                    from novel_agent.services.batch_retry_queue import dismiss_batch_retry

                    dismiss_batch_retry(orch.root_dir, chapter_id)
                except Exception:
                    pass
                try:
                    from novel_agent.services.progress_sync import record_chapter_success

                    record_chapter_success(
                        orch.root_dir,
                        chapter_id,
                        pipeline_complete=orch._chapter_pipeline_complete(chapter_id),
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.error("Chapter %s failed: %s", chapter_id, exc)
            emit_error(chapter_id, str(exc), "run_chapter")
            from novel_agent.exceptions import LLMRateLimitError, TaskAbortedError
            from novel_agent.control.long_run import backoff_on_rate_limit

            if isinstance(exc, TaskAbortedError):
                raise
            if isinstance(exc, LLMRateLimitError):
                await backoff_on_rate_limit(orch.root_dir, consecutive_failures)
            consecutive_failures += 1
            consecutive_skips += 1
            orch._record_batch_retry_skip(
                chapter_id,
                arc_id,
                reason="run_chapter_error",
                message=str(exc),
                step="run_chapter",
            )
            emit_log(
                "warn",
                (
                    f"第 {chapter_id} 章运行异常，已记入待重试队列"
                    f"（{consecutive_failures}/{fail_streak_max}）。"
                    + (
                        "达到跳章保护阈值后将暂停全书批量。"
                        if skip_pause_max > 0
                        else "请尽快在章节维护处理后再续跑。"
                    )
                ),
                "run_chapter",
                chapter_id,
            )
            if consecutive_failures >= fail_streak_max:
                from novel_agent.services.arc_queue import record_novel_batch_paused

                record_novel_batch_paused(
                    orch.root_dir,
                    reason="circuit_breaker",
                    last_chapter=chapter_id,
                    arc_id=arc_id,
                    streak=consecutive_failures,
                )
                emit_progress(
                    "novel_batch",
                    "paused",
                    {
                        "reason": "circuit_breaker",
                        "streak": consecutive_failures,
                        "last_chapter": chapter_id,
                        "arc_id": arc_id,
                    },
                    chapter_id,
                )
                return results, True
            if orch._maybe_pause_after_skip(
                chapter_id, arc_id, consecutive_skips, skip_pause_max
            ):
                return results, True
            continue

        if consecutive_failures >= fail_streak_max:
            from novel_agent.services.arc_queue import record_novel_batch_paused

            record_novel_batch_paused(
                orch.root_dir,
                reason="circuit_breaker",
                last_chapter=chapter_id,
                arc_id=arc_id,
                streak=consecutive_failures,
            )
            emit_progress(
                "novel_batch",
                "paused",
                {
                    "reason": "circuit_breaker",
                    "streak": consecutive_failures,
                    "last_chapter": chapter_id,
                    "arc_id": arc_id,
                },
                chapter_id,
            )
            return results, True

        try:
            ch_num = int(chapter_id)
        except ValueError:
            ch_num = global_offset + i + 1
        if hot_every and ch_num % hot_every == 0:
            orch._auto_compress_assets(threshold=compress_threshold)
        elif warm_every and ch_num % warm_every == 0:
            orch._auto_compress_assets(threshold=max(40, compress_threshold // 2))

        if calibration_interval:
            chapter_num = global_offset + i + 1
            if chapter_num % calibration_interval == 0 and all_chapters_ref:
                orch._write_calibration_report(chapter_id, all_chapters_ref[:chapter_num])

        from novel_agent.control.long_run import resolve_hnsw_rebuild_every

        rebuild_every = resolve_hnsw_rebuild_every(orch.root_dir)
        if rebuild_every and ch_num % rebuild_every == 0 and orch.vector_store:
            try:
                if hasattr(orch.vector_store, "rebuild_hnsw_indices"):
                    orch.vector_store.rebuild_hnsw_indices()
                    emit_progress("vector_index", "rebuilt", {"chapter": chapter_id}, chapter_id)
            except Exception as rebuild_exc:
                logger.warning("HNSW rebuild skipped: %s", rebuild_exc)

        from novel_agent.control.long_run import sleep_inter_chapter

        await sleep_inter_chapter(orch.root_dir)

    return results, False

async def arun_arcs(
    orch,
    arc_id: Optional[str] = None,
    arc_ids: Optional[List[str]] = None,
    start_arc_id: Optional[str] = None,
    resume: bool = True,
    max_chapters: Optional[int] = None,
    ) -> List[ChapterResult]:
    """Generate chapters arc-by-arc using workspace/arc_*.json queues."""
    from novel_agent.services.arc_queue import (
        clear_batch_pause_for_resume,
        filter_briefs_for_resume,
        load_workspace_arcs,
        mark_arc_progress,
        select_arcs,
        sort_briefs_by_dependencies,
    )
    from novel_agent.services.rolling_planner import (
        maybe_open_next_episode,
        prepare_queue_for_run,
        replenish_rolling_window,
    )

    if resume:
        clear_batch_pause_for_resume(orch.root_dir)

    await prepare_queue_for_run(orch)

    arcs = load_workspace_arcs(orch.root_dir)
    if not arcs:
        raise ValueError("No arc_*.json found under workspace; run managing editor / plan novel first.")

    picked = select_arcs(arcs, arc_id=arc_id, arc_ids=arc_ids, start_arc_id=start_arc_id)
    if not picked and (arc_id or arc_ids or start_arc_id):
        raise ValueError(f"No arcs matched arc_id={arc_id!r} start={start_arc_id!r}")

    policy = resolve_runtime_policy(orch.root_dir)
    calibration_interval = int(policy.calibration_interval or 0)
    all_results: List[ChapterResult] = []
    global_offset = 0
    circuit_stopped = False
    chapters_budget = int(max_chapters) if max_chapters and max_chapters > 0 else 0
    all_briefs: List[Dict[str, Any]] = []
    for arc in load_workspace_arcs(orch.root_dir):
        all_briefs.extend(arc.get("chapters") or [])

    use_drain_loop = not arc_id and not arc_ids
    restrict_start_arc = bool(start_arc_id) and use_drain_loop and not arc_id
    idle_rounds = 0
    max_idle_rounds = 3

    while True:
        if circuit_stopped:
            break
        if chapters_budget and len(all_results) >= chapters_budget:
            break

        arcs = load_workspace_arcs(orch.root_dir)
        if arc_id or arc_ids:
            arcs = picked if picked else arcs
        elif restrict_start_arc:
            arcs = select_arcs(arcs, start_arc_id=start_arc_id)
        else:
            arcs = sorted(
                arcs,
                key=lambda a: str(a.get("arc_id") or ""),
            )

        pending_batches: List[tuple] = []
        for arc in arcs:
            aid = str(arc.get("arc_id") or "")
            briefs = sort_briefs_by_dependencies(list(arc.get("chapters") or []))
            if resume:
                briefs = filter_briefs_for_resume(
                    briefs, orch._chapter_pipeline_complete
                )
            if chapters_budget:
                remaining = chapters_budget - len(all_results)
                if remaining <= 0:
                    break
                briefs = briefs[:remaining]
            if briefs:
                pending_batches.append((arc, aid, briefs))

        if not pending_batches:
            if not use_drain_loop:
                break
            added = await replenish_rolling_window(orch)
            await maybe_open_next_episode(orch)
            if added <= 0:
                idle_rounds += 1
                if idle_rounds >= max_idle_rounds:
                    break
            else:
                idle_rounds = 0
            continue

        idle_rounds = 0
        for arc, aid, briefs in pending_batches:
            if chapters_budget and len(all_results) >= chapters_budget:
                break
            emit_progress(
                "arc_batch", "running", {"arc_id": aid, "chapters": len(briefs)}
            )
            mark_arc_progress(orch.root_dir, aid, "running")

            arc_results, stopped = await run_chapter_briefs(orch, 
                briefs,
                arc_id=aid,
                calibration_interval=calibration_interval,
                all_chapters_ref=all_briefs,
                global_offset=global_offset,
            )
            all_results.extend(arc_results)
            global_offset += len(arc.get("chapters") or [])

            last_cid = arc_results[-1].chapter_id if arc_results else ""
            mark_arc_progress(
                orch.root_dir,
                aid,
                "paused" if stopped else "done",
                last_chapter_id=last_cid,
                chapters_done=0,
            )
            emit_progress(
                "arc_batch",
                "paused" if stopped else "done",
                {"arc_id": aid, "completed": len(arc_results)},
            )
            if stopped:
                circuit_stopped = True
                break

        if circuit_stopped:
            break

        if not use_drain_loop:
            break

        await replenish_rolling_window(orch)
        await maybe_open_next_episode(orch)

    if not circuit_stopped:
        pending_left = 0
        try:
            from novel_agent.services.rolling_planner import count_pending_briefs

            pending_left = count_pending_briefs(
                orch.root_dir, orch._chapter_pipeline_complete
            )
        except Exception:
            pass
        if pending_left == 0 and not (chapters_budget and len(all_results) < chapters_budget):
            from novel_agent.services.arc_queue import mark_novel_batch_finished

            mark_novel_batch_finished(orch.root_dir)
    return all_results

async def arun_novel_continue(
    orch,
    resume: bool = True,
    max_chapters: Optional[int] = None,
    *,
    full_book: bool = False,
    ) -> List[ChapterResult]:
    """Resume novel generation from last arc progress.

    full_book=True: drain all arcs with replenish (全书续跑排空), not only from last_arc_id.
    """
    if full_book:
        return await arun_arcs(orch, resume=resume, max_chapters=max_chapters)

    from novel_agent.services.arc_queue import load_arc_progress, load_workspace_arcs

    progress = load_arc_progress(orch.root_dir)
    start_arc = progress.get("last_arc_id")
    if not start_arc:
        arcs = load_workspace_arcs(orch.root_dir)
        if not arcs:
            raise ValueError("No batch progress and no arc files; nothing to continue.")
        start_arc = str(arcs[0].get("arc_id"))
    return await arun_arcs(orch, 
        start_arc_id=start_arc, resume=resume, max_chapters=max_chapters
    )

async def arun_novel(
    orch,
    theme: str,
    genre: str = "玄幻",
    target_chapters: int = 20,
    special_requirements: str = "",
    ) -> List[ChapterResult]:
    logger.info("Starting novel generation asynchronously: theme=%s, genre=%s, chapters=%d",
                theme, genre, target_chapters)
    orch._ensure_project_dirs()
    scale_profile = resolve_scale_profile(target_chapters=target_chapters)
    scale_profile["target_chapters"] = target_chapters
    scale_context = format_scale_profile_for_chief_editor(scale_profile)
    calibration_interval = int(scale_profile.get("calibration_interval") or 0)

    # Step 0: Chief Editor macro outline
    emit_progress("chief_editor", "running")
    theme_kwargs = {
        "theme": theme,
        "genre": genre,
        "target_chapters": target_chapters,
        "special_requirements": special_requirements,
    }
    if orch.config.plugin_manager:
        for hook in orch.config.plugin_manager.get_hooks():
            try:
                theme_kwargs = hook.before_outline(
                    theme_kwargs.get("theme", theme),
                    theme_kwargs.get("genre", genre),
                    **theme_kwargs
                )
            except Exception as e:
                orch._on_hook_error("before_outline", e)

    # Apply potentially modified hook arguments
    theme = theme_kwargs.get("theme", theme)
    genre = theme_kwargs.get("genre", genre)
    target_chapters = theme_kwargs.get("target_chapters", target_chapters)
    special_requirements = theme_kwargs.get("special_requirements", special_requirements)

    if hasattr(orch.chief_editor, "aplan_novel"):
        outline = await orch.chief_editor.aplan_novel(
            theme, genre, target_chapters, special_requirements, scale_context
        )
    else:
        outline = orch.chief_editor.plan_novel(
            theme, genre, target_chapters, special_requirements, scale_context
        )
    outline["scale_profile"] = scale_profile
    outline["target_chapters"] = target_chapters

    if orch.config.plugin_manager:
        for hook in orch.config.plugin_manager.get_hooks():
            try:
                outline = hook.after_outline(outline)
            except Exception as e:
                orch._on_hook_error("after_outline", e)
    orch._write_json(orch.root_dir / "workspace" / "outline.json", outline)
    emit_progress("chief_editor", "done", {
        "title": outline.get("title_options", [""])[0],
        "arcs": len(outline.get("macro_outline", [])),
    })

    # Step 1: Managing Editor splits chapters
    emit_progress("managing_editor", "running")
    if hasattr(orch.managing_editor, "asplit_all_arcs"):
        all_arcs = await orch.managing_editor.asplit_all_arcs(outline)
    else:
        all_arcs = orch.managing_editor.split_all_arcs(outline)
    all_chapters = []
    for arc in all_arcs:
        orch._write_json(orch.root_dir / "workspace" / f"arc_{arc.get('arc_id', 'A01')}.json", arc)
        all_chapters.extend(arc.get("chapters", []))
    emit_progress("managing_editor", "done", {"total_chapters": len(all_chapters), "arcs": len(all_arcs)})

    # Step 2: Generate chapters (arc batches for long/epic runs)
    from novel_agent.services.arc_queue import should_run_by_arc_batches

    scale_name = str(scale_profile.get("scale") or "medium")
    results: List[ChapterResult] = []
    if should_run_by_arc_batches(target_chapters, scale_name):
        for arc in all_arcs:
            aid = str(arc.get("arc_id") or "")
            from novel_agent.services.arc_queue import sort_briefs_by_dependencies

            briefs = sort_briefs_by_dependencies(list(arc.get("chapters") or []))
            emit_progress("arc_batch", "running", {"arc_id": aid, "chapters": len(briefs)})
            arc_results, stopped = await run_chapter_briefs(orch, 
                briefs,
                arc_id=aid,
                calibration_interval=calibration_interval,
                all_chapters_ref=all_chapters,
                global_offset=len(results),
            )
            results.extend(arc_results)
            emit_progress(
                "arc_batch",
                "paused" if stopped else "done",
                {"arc_id": aid, "completed": len(arc_results)},
            )
            if stopped:
                break
    else:
        results, _ = await run_chapter_briefs(orch, 
            all_chapters,
            calibration_interval=calibration_interval,
            all_chapters_ref=all_chapters,
        )

    logger.info(
        "Novel generation completed (Async): %d/%d chapters succeeded",
        len(results),
        len(all_chapters),
    )

    if orch.config.plugin_manager:
        for hook in orch.config.plugin_manager.get_hooks():
            try:
                hook.on_novel_complete(results)
            except Exception as e:
                orch._on_hook_error("on_novel_complete", e)

    return results

