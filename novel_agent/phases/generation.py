import re
import dataclasses
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.phases.base import ChapterContext, PipelinePhase
from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.scripts.merge_scenes import merge_scene_texts
from novel_agent.quality.generation_policy import (
    BOUNDARY_RECHECK_INSTRUCTION,
    should_run_boundary_recheck,
    should_run_generation_style_edit,
)

logger = get_logger("generation_phase")


def _read_text_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _detect_truncation(original: str, edited: str) -> bool:
    """Detect if LLM output was likely truncated."""
    if not edited or not edited.strip():
        return True

    if len(original) < 100:
        return False

    if len(edited) < len(original) * 0.4:
        return True

    stripped = edited.strip()
    last_char = stripped[-1]
    valid_endings = set("。！？…\"'\"）」』】")
    if last_char not in valid_endings:
        if len(edited) >= len(original) * 0.7:
            return False
        return True

    return False


class GenerationPhase(PipelinePhase):
    def execute(self, ctx: ChapterContext) -> ChapterContext:
        """Execute the generation phase steps: scene gen -> merge -> stitch -> style."""
        if not ctx.plan:
            raise ValueError("Context plan is not initialized before generation phase.")

        logger.info("Step 2-5: Generating chapter %s scenes and editing", ctx.chapter_id)
        
        # 1. 运行多线程场景生成
        self._run_scene_generation(ctx)
        
        # 2. 合并场景
        final_text = self._run_merge(ctx)
        
        return dataclasses.replace(ctx, final_text=final_text)

    async def aexecute(self, ctx: ChapterContext) -> ChapterContext:
        """Execute the generation phase steps asynchronously: scene gen -> merge -> stitch -> style."""
        if not ctx.plan:
            raise ValueError("Context plan is not initialized before generation phase.")

        logger.info("Step 2-5: Generating chapter %s scenes and editing (Async)", ctx.chapter_id)
        
        # 1. 运行异步场景生成
        import asyncio
        await self._arun_scene_generation(ctx)
        
        # 2. 合并场景
        final_text = self._run_merge(ctx)
        
        return dataclasses.replace(ctx, final_text=final_text)

    async def _arun_scene_generation(self, ctx: ChapterContext) -> None:
        """Run parallel scene generation using asyncio.gather."""
        import asyncio
        scenes = ctx.plan.get("scenes", [])
        scene_count = len(scenes)
        logger.info("Step 2: Generating %d scenes (Async)", scene_count)
        emit_progress("writer", "running", {"scene_count": scene_count}, ctx.chapter_id)
        
        failed_scenes = []
        
        async def _safe_generate(scene):
            scene_id = scene.get("scene_id")
            try:
                await self._agenerate_scene(ctx.chapter_goal, ctx.chapter_dir, ctx.scenes_dir, scene)
                emit_progress("writer", "done", {"scene_id": scene_id}, ctx.chapter_id)
            except Exception as exc:
                logger.error("Scene %s generation failed: %s", scene_id, exc)
                failed_scenes.append(scene)
                emit_progress("writer", "error", {"scene_id": scene_id, "error": str(exc)}, ctx.chapter_id)
        
        tasks = [_safe_generate(scene) for scene in scenes]
        await asyncio.gather(*tasks)

        if failed_scenes:
            logger.warning("%d scenes failed generation", len(failed_scenes))
            if len(failed_scenes) == scene_count:
                raise RuntimeError(f"All {scene_count} scenes failed to generate. Cannot proceed.")

    async def _agenerate_scene(self, chapter_goal: str, chapter_dir: Path, scenes_dir: Path, scene: Dict[str, Any]) -> None:
        """Generate a single scene asynchronously, adjust length, and write to file."""
        scene_id = scene.get("scene_id", "unknown")
        logger.debug("Generating scene %s (Async)", scene_id)
        
        context = self.orchestrator.context_builder.build(chapter_goal, scene)
        (chapter_dir / f"scene_{scene_id}_context.md").write_text(context, encoding="utf-8")
        
        max_retries = getattr(self.orchestrator.config, "continuity_max_retries", 3)
        draft = await self.orchestrator.writer.awrite_scene(context)

        for attempt in range(max_retries):
            if not hasattr(self.orchestrator, "continuity_checker") or not self.orchestrator.continuity_checker:
                break
            try:
                if hasattr(self.orchestrator.continuity_checker, "acheck"):
                    check_result = await self.orchestrator.continuity_checker.acheck(draft, context)
                else:
                    check_result = self.orchestrator.continuity_checker.check(draft, context)
            except Exception as e:
                logger.warning("Continuity check failed with error: %s", e)
                break

            if check_result.get("pass", False) is True:
                logger.info("Scene %s continuity check passed.", scene_id)
                break
            else:
                issues = check_result.get("issues", [])
                if not issues:
                    break
                feedback = "\n".join(f"- {i.get('why', '冲突')} (建议: {i.get('fix', '无')})" for i in issues)
                logger.warning("Scene %s continuity check failed (Attempt %d/%d):\n%s", scene_id, attempt+1, max_retries, feedback)
                if attempt < max_retries - 1:
                    repair_context = f"{context}\n\n[质检员强制打回：前序草稿存在设定冲突，必须修正以下硬伤]\n{feedback}"
                    draft = await self.orchestrator.writer.awrite_scene(repair_context)
                else:
                    logger.warning("Scene %s continuity check failed after %d attempts. Proceeding with last draft.", scene_id, max_retries)

        target_range = scene.get("target_chars", [400, 800])
        
        if hasattr(self.orchestrator.length_fix, "aadjust"):
            adjusted = await self.orchestrator.length_fix.aadjust(draft, target_range)
        else:
            adjusted = self.orchestrator.length_fix.adjust(draft, target_range)
        
        scene_path = scenes_dir / f"scene_{scene_id}.txt"
        scene_path.write_text(adjusted, encoding="utf-8")

    async def _arun_stitch(self, ctx: ChapterContext, raw_text: str) -> Tuple[str, ChapterContext]:
        """Step 4: Stitch edit merged scenes asynchronously."""
        logger.info("Step 4: Stitch editing (Async)")
        
        scene_files = sorted(ctx.scenes_dir.glob("scene_*.txt"))
        scenes = []
        for path in scene_files:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                scenes.append(content)
                
        if getattr(self.orchestrator.config, "skip_stitch", False) or len(scenes) <= 1:
            logger.info("Skipping stitch stage: skip_stitch config active or only %d scene(s)", len(scenes))
            return raw_text, ctx

        emit_progress("stitch_editor", "running", chapter_id=ctx.chapter_id)
        try:
            if len(scenes) > 1:
                if hasattr(self.orchestrator.stitch_editor, "aedit_scenes"):
                    stitched = await self.orchestrator.stitch_editor.aedit_scenes(scenes)
                else:
                    stitched = self.orchestrator.stitch_editor.edit_scenes(scenes)
            else:
                if hasattr(self.orchestrator.stitch_editor, "aedit"):
                    stitched = await self.orchestrator.stitch_editor.aedit(raw_text)
                else:
                    stitched = self.orchestrator.stitch_editor.edit(raw_text)
            (ctx.chapter_dir / "chapter_merged.txt").write_text(stitched, encoding="utf-8")
        except Exception as exc:
            logger.error("Stitch editing failed: %s", exc)
            stitched = raw_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Stitch editing failed: {exc}. Fallback to raw merged content.",))
        emit_progress("stitch_editor", "done", chapter_id=ctx.chapter_id)
        return stitched, ctx

    def _generation_style_enabled(self) -> bool:
        return should_run_generation_style_edit(
            self.orchestrator.root_dir,
            skip_style_edit=getattr(self.orchestrator.config, "skip_style_edit", False),
        )

    async def _arun_style_edit(self, ctx: ChapterContext, stitched_text: str, raw_text: str) -> Tuple[str, ChapterContext]:
        """Step 5: Style editing asynchronously and handle truncation mitigation."""
        if not self._generation_style_enabled():
            logger.info(
                "Skipping generation Style Editor (mode=%s or token downgrade).",
                "skip_style_edit" if getattr(self.orchestrator.config, "skip_style_edit", False) else "policy",
            )
            return stitched_text, ctx

        logger.info("Step 5: Style editing (Async)")
        emit_progress("style_editor", "running", chapter_id=ctx.chapter_id)
        try:
            if hasattr(self.orchestrator.style_editor, "aedit"):
                final_text = await self.orchestrator.style_editor.aedit(stitched_text)
            else:
                final_text = self.orchestrator.style_editor.edit(stitched_text)
        except Exception as exc:
            logger.error("Style editing failed: %s", exc)
            final_text = stitched_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Style editing failed: {exc}. Fallback to stitched content.",))
        emit_progress("style_editor", "done", {"chars": len(final_text)}, ctx.chapter_id)

        # Truncation detection and fallback
        if _detect_truncation(raw_text, final_text):
            logger.warning(
                "Truncation detected in style_editor output (raw=%d, final=%d chars). "
                "Falling back to stitched version.",
                len(raw_text), len(final_text),
            )
            final_text = stitched_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + ("Truncation detected in style_editor. Fallback to stitched content.",))
            if _detect_truncation(raw_text, stitched_text):
                logger.warning("Stitched output also truncated, using raw merge")
                final_text = raw_text
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + ("Stitched output also truncated. Fallback to raw merge content.",))

        return final_text, ctx

    def _finalize_boundary_recheck(
        self,
        ctx: ChapterContext,
        original: str,
        revised: str,
    ) -> Tuple[str, ChapterContext]:
        if not revised or not revised.strip():
            return original, ctx
        cleaned = revised.strip()
        if _detect_truncation(original, cleaned):
            logger.warning(
                "Truncation detected in boundary recheck (before=%d, after=%d). Keeping prior text.",
                len(original),
                len(cleaned),
            )
            ctx = dataclasses.replace(
                ctx,
                warnings=ctx.warnings
                + ("Boundary recheck output truncated; kept pre-recheck chapter text.",),
            )
            return original, ctx
        (ctx.chapter_dir / "chapter_boundary_recheck.txt").write_text(cleaned, encoding="utf-8")
        return cleaned, ctx

    async def _arun_boundary_recheck(
        self,
        ctx: ChapterContext,
        text: str,
        style_ran: bool,
        scene_count: int,
    ) -> Tuple[str, ChapterContext]:
        if not should_run_boundary_recheck(
            self.orchestrator.root_dir, style_ran=style_ran, scene_count=scene_count
        ) or not (text or "").strip():
            return text, ctx
        logger.info("Step 5b: Boundary recheck (%d scenes)", scene_count)
        emit_progress("stitch_editor", "running", {"phase": "boundary_recheck"}, ctx.chapter_id)
        prompt = (text.strip() + BOUNDARY_RECHECK_INSTRUCTION).strip()
        try:
            if hasattr(self.orchestrator.stitch_editor, "aedit"):
                revised = await self.orchestrator.stitch_editor.aedit(prompt)
            else:
                revised = self.orchestrator.stitch_editor.edit(prompt)
            final_text, ctx = self._finalize_boundary_recheck(ctx, text, revised or "")
            emit_progress("stitch_editor", "done", {"phase": "boundary_recheck"}, ctx.chapter_id)
            return final_text, ctx
        except Exception as exc:
            logger.warning("Boundary recheck failed: %s", exc)
            ctx = dataclasses.replace(
                ctx, warnings=ctx.warnings + (f"Boundary recheck after style failed: {exc}.",)
            )
        emit_progress("stitch_editor", "done", {"phase": "boundary_recheck", "skipped": True}, ctx.chapter_id)
        return text, ctx

    def _run_boundary_recheck(
        self,
        ctx: ChapterContext,
        text: str,
        style_ran: bool,
        scene_count: int,
    ) -> Tuple[str, ChapterContext]:
        if not should_run_boundary_recheck(
            self.orchestrator.root_dir, style_ran=style_ran, scene_count=scene_count
        ) or not (text or "").strip():
            return text, ctx
        logger.info("Step 5b: Boundary recheck (%d scenes)", scene_count)
        emit_progress("stitch_editor", "running", {"phase": "boundary_recheck"}, ctx.chapter_id)
        prompt = (text.strip() + BOUNDARY_RECHECK_INSTRUCTION).strip()
        try:
            revised = self.orchestrator.stitch_editor.edit(prompt)
            final_text, ctx = self._finalize_boundary_recheck(ctx, text, revised or "")
            emit_progress("stitch_editor", "done", {"phase": "boundary_recheck"}, ctx.chapter_id)
            return final_text, ctx
        except Exception as exc:
            logger.warning("Boundary recheck failed: %s", exc)
            ctx = dataclasses.replace(
                ctx, warnings=ctx.warnings + (f"Boundary recheck after style failed: {exc}.",)
            )
        emit_progress("stitch_editor", "done", {"phase": "boundary_recheck", "skipped": True}, ctx.chapter_id)
        return text, ctx

    def _run_scene_generation(self, ctx: ChapterContext) -> None:
        """Run parallel scene generation using ThreadPoolExecutor."""
        scenes = ctx.plan.get("scenes", [])
        scene_count = len(scenes)
        logger.info("Step 2: Generating %d scenes", scene_count)
        emit_progress("writer", "running", {"scene_count": scene_count}, ctx.chapter_id)
        
        max_workers = max(1, min(scene_count, self.config.max_workers))
        failed_scenes = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._generate_scene, ctx.chapter_goal, ctx.chapter_dir, ctx.scenes_dir, scene
                ): scene for scene in scenes
            }
            try:
                for future in as_completed(futures, timeout=600):
                    scene = futures[future]
                    try:
                        future.result()
                        emit_progress("writer", "done", {"scene_id": scene.get("scene_id")}, ctx.chapter_id)
                    except Exception as exc:
                        logger.error("Scene %s generation failed: %s", scene.get("scene_id"), exc)
                        failed_scenes.append(scene)
                        emit_progress("writer", "error", {"scene_id": scene.get("scene_id"), "error": str(exc)}, ctx.chapter_id)
            except TimeoutError:
                logger.error("Scene generation timed out for chapter %s", ctx.chapter_id)
                for f in futures:
                    f.cancel()
                done_ids = {id(f) for f in futures if f.done()}
                for f, scene in futures.items():
                    if id(f) not in done_ids:
                        failed_scenes.append(scene)

        if failed_scenes:
            logger.warning("%d scenes failed generation", len(failed_scenes))
            if len(failed_scenes) == scene_count:
                raise RuntimeError(f"All {scene_count} scenes failed to generate. Cannot proceed.")

    def _generate_scene(self, chapter_goal: str, chapter_dir: Path, scenes_dir: Path, scene: Dict[str, Any]) -> None:
        """Generate a single scene, adjust length, and write to file."""
        scene_id = scene.get("scene_id", "unknown")
        logger.debug("Generating scene %s", scene_id)
        
        context = self.orchestrator.context_builder.build(chapter_goal, scene)
        (chapter_dir / f"scene_{scene_id}_context.md").write_text(context, encoding="utf-8")
        
        max_retries = getattr(self.orchestrator.config, "continuity_max_retries", 3)
        draft = self.orchestrator.writer.write_scene(context)

        for attempt in range(max_retries):
            if not hasattr(self.orchestrator, "continuity_checker") or not self.orchestrator.continuity_checker:
                break
            try:
                check_result = self.orchestrator.continuity_checker.check(draft, context)
            except Exception as e:
                logger.warning("Continuity check failed with error: %s", e)
                break

            if check_result.get("pass", False) is True:
                logger.info("Scene %s continuity check passed.", scene_id)
                break
            else:
                issues = check_result.get("issues", [])
                if not issues:
                    break
                feedback = "\n".join(f"- {i.get('why', '冲突')} (建议: {i.get('fix', '无')})" for i in issues)
                logger.warning("Scene %s continuity check failed (Attempt %d/%d):\n%s", scene_id, attempt+1, max_retries, feedback)
                if attempt < max_retries - 1:
                    repair_context = f"{context}\n\n[质检员强制打回：前序草稿存在设定冲突，必须修正以下硬伤]\n{feedback}"
                    draft = self.orchestrator.writer.write_scene(repair_context)
                else:
                    logger.warning("Scene %s continuity check failed after %d attempts. Proceeding with last draft.", scene_id, max_retries)

        target_range = scene.get("target_chars", [400, 800])
        adjusted = self.orchestrator.length_fix.adjust(draft, target_range)
        
        scene_path = scenes_dir / f"scene_{scene_id}.txt"
        scene_path.write_text(adjusted, encoding="utf-8")

    def _run_merge(self, ctx: ChapterContext) -> str:
        """Step 3: Merge scenes into raw chapter text."""
        logger.info("Step 3: Merging scenes")
        emit_progress("merge", "running", chapter_id=ctx.chapter_id)
        try:
            raw_chapter = merge_scene_texts(ctx.scenes_dir)
            if not raw_chapter or not raw_chapter.strip():
                raise RuntimeError("Merged chapter is empty. No valid scene content found.")
            (ctx.chapter_dir / "chapter_raw.txt").write_text(raw_chapter, encoding="utf-8")
            emit_progress("merge", "done", {"chars": len(raw_chapter)}, ctx.chapter_id)
            return raw_chapter
        except Exception as exc:
            logger.error("Scene merging failed: %s", exc)
            raise RuntimeError(f"Scene merging failed: {exc}") from exc

    def _run_stitch(self, ctx: ChapterContext, raw_text: str) -> Tuple[str, ChapterContext]:
        """Step 4: Stitch edit merged scenes to smooth transitions."""
        logger.info("Step 4: Stitch editing")
        
        scene_files = sorted(ctx.scenes_dir.glob("scene_*.txt"))
        scenes = []
        for path in scene_files:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                scenes.append(content)
                
        if getattr(self.orchestrator.config, "skip_stitch", False) or len(scenes) <= 1:
            logger.info("Skipping stitch stage: skip_stitch config active or only %d scene(s)", len(scenes))
            return raw_text, ctx

        emit_progress("stitch_editor", "running", chapter_id=ctx.chapter_id)
        try:
            if len(scenes) > 1:
                stitched = self.orchestrator.stitch_editor.edit_scenes(scenes)
            else:
                stitched = self.orchestrator.stitch_editor.edit(raw_text)
            (ctx.chapter_dir / "chapter_merged.txt").write_text(stitched, encoding="utf-8")
        except Exception as exc:
            logger.error("Stitch editing failed: %s", exc)
            stitched = raw_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Stitch editing failed: {exc}. Fallback to raw merged content.",))
        emit_progress("stitch_editor", "done", chapter_id=ctx.chapter_id)
        return stitched, ctx

    def _run_style_edit(self, ctx: ChapterContext, stitched_text: str, raw_text: str) -> Tuple[str, ChapterContext]:
        """Step 5: Style editing and handle truncation mitigation."""
        if not self._generation_style_enabled():
            logger.info(
                "Skipping generation Style Editor (mode=%s or token downgrade).",
                "skip_style_edit" if getattr(self.orchestrator.config, "skip_style_edit", False) else "policy",
            )
            return stitched_text, ctx

        logger.info("Step 5: Style editing")
        emit_progress("style_editor", "running", chapter_id=ctx.chapter_id)
        try:
            final_text = self.orchestrator.style_editor.edit(stitched_text)
        except Exception as exc:
            logger.error("Style editing failed: %s", exc)
            final_text = stitched_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Style editing failed: {exc}. Fallback to stitched content.",))
        emit_progress("style_editor", "done", {"chars": len(final_text)}, ctx.chapter_id)

        # Truncation detection and fallback
        if _detect_truncation(raw_text, final_text):
            logger.warning(
                "Truncation detected in style_editor output (raw=%d, final=%d chars). "
                "Falling back to stitched version.",
                len(raw_text), len(final_text),
            )
            final_text = stitched_text
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + ("Truncation detected in style_editor. Fallback to stitched content.",))
            if _detect_truncation(raw_text, stitched_text):
                logger.warning("Stitched output also truncated, using raw merge")
                final_text = raw_text
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + ("Stitched output also truncated. Fallback to raw merge content.",))

        return final_text, ctx
