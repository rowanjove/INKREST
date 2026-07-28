import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Tuple

from novel_agent.phases.base import ChapterContext, PipelinePhase
from novel_agent.state.persist_stamp import (
    compute_persist_stamp,
    load_persist_stamp,
    write_persist_stamp,
)
from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.scripts.sensitive_scan import scan_sensitive_words

logger = get_logger("post_audit_phase")


class PostAuditPhase(PipelinePhase):
    def execute(self, ctx: ChapterContext) -> Tuple[ChapterContext, bool]:
        """Execute post-audit phase: sensitive scan, approval gate, and state persistence.
        
        Returns:
            Tuple[ChapterContext, bool]: The updated context and whether it was approved.
        """
        logger.info("Step 11-13: Post-audit scanning, approval gate and state updates for chapter %s", ctx.chapter_id)
        
        # 1. 敏感词扫描
        self._run_sensitive_scan(ctx)
        
        # 2. 审批闸
        approved = self.orchestrator.approval_gate.request_approval(ctx.chapter_id, ctx.chapter_dir)
        if not approved:
            logger.info("Chapter %s not approved at approval gate", ctx.chapter_id)
            emit_progress("approval", "skipped", chapter_id=ctx.chapter_id)
            return ctx, False
            
        # 3. 提取与合并伏笔信息
        state_update = self._extract_and_merge_hooks(ctx)
        
        # 4. 持久化数据状态
        self._apply_state_persistence(ctx, state_update)
        
        # 交互模式下，如果审批通过，将 pending 状态一键批准并落库及同步 YAML 镜像
        if self.orchestrator.config.interactive:
            self.orchestrator.store.accept_chapter_candidates(ctx.chapter_id)
            self.orchestrator.state_manager._apply_yaml_compat_update(state_update)
        
        return ctx, True

    async def aexecute(self, ctx: ChapterContext) -> Tuple[ChapterContext, bool]:
        """Execute post-audit phase asynchronously: sensitive scan, approval gate, and state persistence.
        
        Returns:
            Tuple[ChapterContext, bool]: The updated context and whether it was approved.
        """
        logger.info("Step 11-13: Post-audit scanning, approval gate and state updates for chapter %s (Async)", ctx.chapter_id)
        
        # 1. 敏感词扫描
        self._run_sensitive_scan(ctx)
        
        # 2. 审批闸
        if hasattr(self.orchestrator.approval_gate, "arequest_approval"):
            approved = await self.orchestrator.approval_gate.arequest_approval(ctx.chapter_id, ctx.chapter_dir)
        else:
            approved = self.orchestrator.approval_gate.request_approval(ctx.chapter_id, ctx.chapter_dir)
            
        if not approved:
            logger.info("Chapter %s not approved at approval gate", ctx.chapter_id)
            emit_progress("approval", "skipped", chapter_id=ctx.chapter_id)
            return ctx, False
            
        # 3. 提取与合并伏笔信息
        state_update = self._extract_and_merge_hooks(ctx)
        
        # 4. 持久化数据状态
        await self._aapply_state_persistence(ctx, state_update)
        
        # 交互模式下，如果审批通过，将 pending 状态一键批准并落库及同步 YAML 镜像
        if self.orchestrator.config.interactive:
            db_res = self.orchestrator.store.accept_chapter_candidates(ctx.chapter_id)
            import asyncio
            if asyncio.isfuture(db_res) or asyncio.iscoroutine(db_res):
                await db_res
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.orchestrator.state_manager._apply_yaml_compat_update, state_update)
        
        return ctx, True

    def _persist_stamp_path(self, ctx: ChapterContext) -> Path:
        return ctx.reports_dir / "post_audit_stamp.json"

    def _should_skip_duplicate_persist(
        self, ctx: ChapterContext, state_update: Dict[str, Any]
    ) -> bool:
        stamp = compute_persist_stamp(
            ctx.chapter_id, ctx.final_text or "", state_update
        )
        if stamp and stamp == load_persist_stamp(self._persist_stamp_path(ctx)):
            logger.info(
                "Skipping duplicate post_audit persistence for chapter %s",
                ctx.chapter_id,
            )
            return True
        return False

    async def _aapply_state_persistence(self, ctx: ChapterContext, state_update: Dict[str, Any]) -> None:
        """Step 13: Apply state updates asynchronously to state managers and SQLite database."""
        if self._should_skip_duplicate_persist(ctx, state_update):
            emit_progress(
                "state_update",
                "skipped",
                {"reason": "idempotent"},
                chapter_id=ctx.chapter_id,
            )
            return

        logger.info("Step 13: Persistence update for chapter %s (Async)", ctx.chapter_id)
        emit_progress("state_update", "running", chapter_id=ctx.chapter_id)
        
        # 1. 保存 YAML 文件
        await self.orchestrator.state_manager.aapply_update(ctx.chapter_id, state_update, interactive=self.orchestrator.config.interactive)
        
        # 2. 保存关系型章节索引到 SQLite
        chapter_title = ctx.plan.get("chapter_title", "") if ctx.plan else ""
        final_path = ctx.chapter_dir / "chapter_final.txt"
        word_count = ctx.wordcount.get("count", 0) if ctx.wordcount else 0
        risk_level = ctx.audit.get("risk_level", "") if ctx.audit else ""
        
        db_res = self.orchestrator.store.index_chapter(
            chapter_id=ctx.chapter_id,
            title=chapter_title,
            final_path=final_path,
            word_count=word_count,
            risk_level=risk_level,
        )
        import asyncio
        if asyncio.isfuture(db_res) or asyncio.iscoroutine(db_res):
            await db_res
            
        # 3. 保存章节摘要到 SQLite
        summary_path = ctx.chapter_dir / "chapter_summary.md"
        db_res2 = self.orchestrator.store.save_chapter_summary(
            chapter_id=ctx.chapter_id,
            summary=ctx.chapter_summary or "",
            summary_path=summary_path,
        )
        if asyncio.isfuture(db_res2) or asyncio.iscoroutine(db_res2):
            await db_res2

        write_persist_stamp(
            self._persist_stamp_path(ctx),
            compute_persist_stamp(ctx.chapter_id, ctx.final_text or "", state_update),
            ctx.chapter_id,
        )
            
        emit_progress("state_update", "done", chapter_id=ctx.chapter_id)

    def _run_sensitive_scan(self, ctx: ChapterContext) -> None:
        """Step 11: Scan for sensitive words in final text."""
        emit_progress("sensitive_scan", "running", chapter_id=ctx.chapter_id)
        sensitive_words_path = self.orchestrator.root_dir / "assets" / "sensitive_words.txt"
        
        sensitive_report = scan_sensitive_words(ctx.final_text, sensitive_words_path)
        self.orchestrator._write_json(ctx.reports_dir / "sensitive_scan.json", sensitive_report)
        emit_progress("sensitive_scan", "done", chapter_id=ctx.chapter_id)

    def _extract_and_merge_hooks(self, ctx: ChapterContext) -> Dict[str, Any]:
        """Extract narrative hooks from audit report and merge them into state_update."""
        state_update = dict(ctx.extracted_state or {})
        audit_data = ctx.audit or {}
        narrative_hooks = audit_data.get("narrative_hooks", [])
        
        if narrative_hooks:
            existing_hooks = state_update.get("hooks", [])
            if not isinstance(existing_hooks, list):
                existing_hooks = []
            
            for idx, item in enumerate(narrative_hooks):
                description = item.get("description") or item.get("text") or str(item) if isinstance(item, dict) else str(item)
                title = item.get("title") or item.get("text") or str(item)[:24] if isinstance(item, dict) else str(item)[:24]
                
                hook_entry = {
                    "id": f"H_{ctx.chapter_id}_{idx + 1:02d}",
                    "title": title,
                    "status": "open",
                    "description": description,
                }
                existing_hooks.append(hook_entry)
            state_update["hooks"] = existing_hooks
            
        return state_update

    def _apply_state_persistence(self, ctx: ChapterContext, state_update: Dict[str, Any]) -> None:
        """Step 13: Apply state updates to state managers and SQLite database."""
        if self._should_skip_duplicate_persist(ctx, state_update):
            emit_progress(
                "state_update",
                "skipped",
                {"reason": "idempotent"},
                chapter_id=ctx.chapter_id,
            )
            return

        logger.info("Step 13: Persistence update for chapter %s", ctx.chapter_id)
        emit_progress("state_update", "running", chapter_id=ctx.chapter_id)
        
        # 1. 保存 YAML 文件
        self.orchestrator.state_manager.apply_update(ctx.chapter_id, state_update, interactive=self.orchestrator.config.interactive)
        
        # 2. 保存关系型章节索引到 SQLite
        chapter_title = ctx.plan.get("chapter_title", "") if ctx.plan else ""
        final_path = ctx.chapter_dir / "chapter_final.txt"
        word_count = ctx.wordcount.get("count", 0) if ctx.wordcount else 0
        risk_level = ctx.audit.get("risk_level", "") if ctx.audit else ""
        
        self.orchestrator.store.index_chapter(
            chapter_id=ctx.chapter_id,
            title=chapter_title,
            final_path=final_path,
            word_count=word_count,
            risk_level=risk_level,
        )
        
        # 3. 保存章节摘要到 SQLite
        summary_path = ctx.chapter_dir / "chapter_summary.md"
        self.orchestrator.store.save_chapter_summary(
            chapter_id=ctx.chapter_id,
            summary=ctx.chapter_summary or "",
            summary_path=summary_path,
        )
        write_persist_stamp(
            self._persist_stamp_path(ctx),
            compute_persist_stamp(ctx.chapter_id, ctx.final_text or "", state_update),
            ctx.chapter_id,
        )
        emit_progress("state_update", "done", chapter_id=ctx.chapter_id)
