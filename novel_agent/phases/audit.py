import json
import dataclasses
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from novel_agent.phases.base import ChapterContext, PipelinePhase
from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.quality.audit_schema import validate_audit_report
from novel_agent.quality.audit_rewrite import audit_requires_rewrite
from novel_agent.quality.generation_policy import should_length_fix_after_audit_rewrite
from novel_agent.quality.audit_persist import split_audit_for_persist
from novel_agent.quality.style_precheck import write_style_precheck_cache
from novel_agent.phases.audit_matching import find_best_paragraph_match
from novel_agent.phases.audit_rewrite import AuditRewriteMixin
from novel_agent.scripts.count_chars import wordcount_report

logger = get_logger("audit_phase")


class AuditPhase(AuditRewriteMixin, PipelinePhase):
    def _persist_audit_report(self, ctx: ChapterContext, audit: Dict[str, Any]) -> Dict[str, Any]:
        """Write audit.json without internal-only fields; return full audit dict."""
        public, _ = split_audit_for_persist(audit)
        self.orchestrator._write_json(ctx.reports_dir / "audit.json", public)
        return audit

    def _write_style_precheck_from_audit(
        self, ctx: ChapterContext, final_text: str, audit: Dict[str, Any]
    ) -> None:
        _, checks = split_audit_for_persist(audit)
        write_style_precheck_cache(
            ctx.reports_dir,
            final_text,
            self.orchestrator.root_dir,
            checks=checks,
        )

    def _get_audit_args(self, ctx: ChapterContext) -> Tuple[dict, list, list, dict]:
        state = self.orchestrator.state_manager.get_state()
        target_chars = ctx.plan.get("target_chars") if ctx.plan else None
        if not target_chars:
            target_chars = [1200, 2200]
            if hasattr(self.config, "chapter"):
                target_chars = getattr(self.config.chapter, "default_target_chars", [1200, 2200])
        
        from novel_agent.scripts.sensitive_scan import load_sensitive_words
        sensitive_words_path = self.orchestrator.root_dir / "assets" / "sensitive_words.txt"
        sensitive_words = load_sensitive_words(sensitive_words_path)
        
        plan = ctx.plan or {}
        return state, target_chars, sensitive_words, plan

    def _resolve_max_rewrites(self) -> int:
        from novel_agent.control.long_run import resolve_audit_max_rewrites
        from novel_agent.control.runtime_policy import get_audit_profile_flags

        max_rewrites = resolve_audit_max_rewrites(self.orchestrator.root_dir)
        override = get_audit_profile_flags(self.orchestrator.root_dir).get("max_rewrites_override")
        if override is not None:
            return int(override)
        return max_rewrites

    def execute(self, ctx: ChapterContext) -> ChapterContext:
        """Execute the audit phase: continuity, summary, wordcount, audit, rewrite loop."""
        if ctx.final_text is None:
            raise ValueError("Context final_text must be set before audit phase.")

        logger.info("Steps 6-10: Auditing and reviewing chapter %s", ctx.chapter_id)
        
        # 1. 一致性检查与总结 (并行)
        continuity_state = self.orchestrator.state_manager.get_state()
        continuity_state_text = json.dumps(continuity_state, ensure_ascii=False, indent=2)
        summary, ctx = self._run_continuity_and_summary(ctx, continuity_state_text)
        
        # 2. 字数统计
        wc = self._run_wordcount(ctx)
        
        # 3. 审计与状态提取 (并行)
        audit, ext_state, ctx = self._run_audit_and_extraction(ctx, summary)
        
        # 4. 自适应重写循环
        final_text, final_audit, ctx = self._run_rewrite_loop(
            ctx, audit, ext_state, wc, summary, continuity_state_text
        )

        self._write_style_precheck_from_audit(ctx, final_text, final_audit)

        return dataclasses.replace(
            ctx,
            final_text=final_text,
            audit=final_audit,
            chapter_summary=summary,
            wordcount=wc,
            extracted_state=ext_state
        )

    async def aexecute(self, ctx: ChapterContext) -> ChapterContext:
        """Execute the audit phase asynchronously: continuity, summary, wordcount, audit, rewrite loop."""
        if ctx.final_text is None:
            raise ValueError("Context final_text must be set before audit phase.")

        logger.info("Steps 6-10: Auditing and reviewing chapter %s (Async)", ctx.chapter_id)

        from novel_agent.control.runtime_policy import get_audit_profile_flags

        audit_flags = get_audit_profile_flags(self.orchestrator.root_dir)

        # 1. 一致性检查与总结 (异步并行)
        continuity_state = self.orchestrator.state_manager.get_state()
        continuity_state_text = json.dumps(continuity_state, ensure_ascii=False, indent=2)
        if audit_flags.get("skip_continuity") and audit_flags.get("skip_chapter_summary"):
            summary = f"章节 {ctx.chapter_id}（审校精简档：跳过连续性与摘要 LLM）"
            stub = {"pass": True, "issues": [], "skipped": True, "reason": "audit_profile"}
            self.orchestrator._write_json(ctx.reports_dir / "continuity.json", stub)
            (ctx.chapter_dir / "chapter_summary.md").write_text(summary, encoding="utf-8")
            emit_progress("continuity_checker", "skipped", {"reason": "audit_profile"}, ctx.chapter_id)
            emit_progress("chapter_summary", "skipped", {"reason": "audit_profile"}, ctx.chapter_id)
        elif audit_flags.get("skip_continuity"):
            stub = {"pass": True, "issues": [], "skipped": True, "reason": "audit_profile"}
            self.orchestrator._write_json(ctx.reports_dir / "continuity.json", stub)
            emit_progress("continuity_checker", "skipped", {"reason": "audit_profile"}, ctx.chapter_id)
            summary, ctx = await self._arun_summary_only(ctx)
        elif audit_flags.get("skip_chapter_summary"):
            emit_progress("chapter_summary", "skipped", {"reason": "audit_profile"}, ctx.chapter_id)
            summary, ctx = await self._arun_continuity_only(ctx, continuity_state_text)
        else:
            summary, ctx = await self._arun_continuity_and_summary(ctx, continuity_state_text)
        
        # 2. 字数统计
        wc = self._run_wordcount(ctx)
        
        # 3. 审计与状态提取 (异步并行)
        audit, ext_state, ctx = await self._arun_audit_and_extraction(ctx, summary)
        
        # 4. 自适应重写循环
        final_text, final_audit, ctx = await self._arun_rewrite_loop(
            ctx, audit, ext_state, wc, summary, continuity_state_text
        )

        self._write_style_precheck_from_audit(ctx, final_text, final_audit)

        return dataclasses.replace(
            ctx,
            final_text=final_text,
            audit=final_audit,
            chapter_summary=summary,
            wordcount=wc,
            extracted_state=ext_state
        )

    async def _arun_continuity_and_summary(self, ctx: ChapterContext, state_text: str) -> Tuple[str, ChapterContext]:
        """Step 6+8: Run continuity check and chapter summary in parallel asynchronously."""
        emit_progress("continuity_checker", "running", chapter_id=ctx.chapter_id)
        emit_progress("chapter_summary", "running", chapter_id=ctx.chapter_id)
        
        import asyncio

        async def _run_cont():
            nonlocal ctx
            try:
                if hasattr(self.orchestrator.continuity_checker, "acheck"):
                    return await self.orchestrator.continuity_checker.acheck(ctx.final_text, state_text)
                return self.orchestrator.continuity_checker.check(ctx.final_text, state_text)
            except Exception as exc:
                logger.error("Rewrite continuity check failed: %s", exc)
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Continuity check failed: {exc}.",))
                return {"pass": False, "issues": [{"type": "error", "detail": str(exc)}]}

        async def _run_summ():
            nonlocal ctx
            try:
                if hasattr(self.orchestrator.chapter_summary_agent, "asummarize"):
                    return await self.orchestrator.chapter_summary_agent.asummarize(ctx.final_text)
                return self.orchestrator.chapter_summary_agent.summarize(ctx.final_text)
            except Exception as exc:
                logger.error("Chapter summary failed: %s", exc)
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Chapter summary failed: {exc}.",))
                return f"章节总结生成失败: {exc}"

        cont_report, ch_summary = await asyncio.gather(_run_cont(), _run_summ())

        self.orchestrator._write_json(ctx.reports_dir / "continuity.json", cont_report)
        emit_progress("continuity_checker", "done", {"pass": cont_report.get("pass", False)}, ctx.chapter_id)
        
        (ctx.chapter_dir / "chapter_summary.md").write_text(ch_summary, encoding="utf-8")
        emit_progress("chapter_summary", "done", chapter_id=ctx.chapter_id)
        return ch_summary, ctx

    async def _arun_summary_only(self, ctx: ChapterContext) -> Tuple[str, ChapterContext]:
        emit_progress("chapter_summary", "running", chapter_id=ctx.chapter_id)
        try:
            if hasattr(self.orchestrator.chapter_summary_agent, "asummarize"):
                ch_summary = await self.orchestrator.chapter_summary_agent.asummarize(ctx.final_text)
            else:
                ch_summary = self.orchestrator.chapter_summary_agent.summarize(ctx.final_text)
        except Exception as exc:
            logger.error("Chapter summary failed: %s", exc)
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Chapter summary failed: {exc}.",))
            ch_summary = f"章节总结生成失败: {exc}"
        (ctx.chapter_dir / "chapter_summary.md").write_text(ch_summary, encoding="utf-8")
        emit_progress("chapter_summary", "done", chapter_id=ctx.chapter_id)
        return ch_summary, ctx

    async def _arun_continuity_only(
        self, ctx: ChapterContext, state_text: str
    ) -> Tuple[str, ChapterContext]:
        emit_progress("continuity_checker", "running", chapter_id=ctx.chapter_id)
        try:
            if hasattr(self.orchestrator.continuity_checker, "acheck"):
                cont_report = await self.orchestrator.continuity_checker.acheck(
                    ctx.final_text, state_text
                )
            else:
                cont_report = self.orchestrator.continuity_checker.check(ctx.final_text, state_text)
        except Exception as exc:
            logger.error("Continuity check failed: %s", exc)
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Continuity check failed: {exc}.",))
            cont_report = {"pass": False, "issues": [{"type": "error", "detail": str(exc)}]}
        self.orchestrator._write_json(ctx.reports_dir / "continuity.json", cont_report)
        emit_progress(
            "continuity_checker",
            "done",
            {"pass": cont_report.get("pass", False)},
            ctx.chapter_id,
        )
        summary_path = ctx.chapter_dir / "chapter_summary.md"
        summary = (
            summary_path.read_text(encoding="utf-8").strip()
            if summary_path.is_file()
            else f"章节 {ctx.chapter_id}"
        )
        return summary, ctx

    async def _arun_audit_and_extraction(self, ctx: ChapterContext, summary: str) -> Tuple[Dict[str, Any], Dict[str, Any], ChapterContext]:
        """Step 10a+10b: Audit prose and extract state in parallel asynchronously."""
        emit_progress("auditor", "running", chapter_id=ctx.chapter_id)
        emit_progress("state_extractor", "running", chapter_id=ctx.chapter_id)
        
        import asyncio

        async def _run_audit():
            nonlocal ctx
            try:
                state, target_chars, sensitive_words, plan = self._get_audit_args(ctx)
                if hasattr(self.orchestrator.auditor, "aaudit"):
                    audit_res = await self.orchestrator.auditor.aaudit(
                        ctx.final_text, state=state, target_chars=target_chars, sensitive_words=sensitive_words, plan=plan
                    )
                else:
                    audit_res = self.orchestrator.auditor.audit(
                        ctx.final_text, state=state, target_chars=target_chars, sensitive_words=sensitive_words, plan=plan
                    )
                validate_audit_report(audit_res)
                return audit_res
            except Exception as exc:
                logger.warning("Audit failed or invalid: %s", exc)
                ctx = dataclasses.replace(
                    ctx,
                    warnings=ctx.warnings + (f"Audit agent failed or output invalid: {exc}. Fallback to low-risk audit schema.",)
                )
                return {"risk_level": "低", "issues": [], "state_update": {}}

        async def _run_extract():
            nonlocal ctx
            try:
                if hasattr(self.orchestrator.state_extractor, "aextract"):
                    return await self.orchestrator.state_extractor.aextract(ctx.final_text, ctx.chapter_id, summary)
                return self.orchestrator.state_extractor.extract(ctx.final_text, ctx.chapter_id, summary)
            except Exception as exc:
                logger.error("State extraction failed: %s", exc)
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"State extraction failed: {exc}.",))
                return {"events": [], "characters": {}, "objects": [], "threads": []}

        audit, ext_state = await asyncio.gather(_run_audit(), _run_extract())

        self._persist_audit_report(ctx, audit)
        self.orchestrator._write_json(ctx.chapter_dir / "state_update.json", ext_state)
        
        emit_progress("auditor", "done", {"risk_level": audit.get("risk_level", "unknown")}, ctx.chapter_id)
        emit_progress("state_extractor", "done", {"events": len(ext_state.get("events", []))}, ctx.chapter_id)
        return audit, ext_state, ctx

    async def _arun_rewrite_loop(
        self,
        ctx: ChapterContext,
        audit: Dict[str, Any],
        ext_state: Dict[str, Any],
        wc: Dict[str, Any],
        summary: str,
        state_text: str
    ) -> Tuple[str, Dict[str, Any], ChapterContext]:
        """Step 10b: Execute self-adaptive rewrite loop asynchronously."""
        max_rewrites = self._resolve_max_rewrites()
        final_text = ctx.final_text
        current_audit = audit

        for rewrite_attempt in range(max_rewrites):
            if not audit_requires_rewrite(current_audit, root_dir=self.orchestrator.root_dir):
                break
            
            logger.info("Rewrite attempt %d/%d for chapter %s (risk=高) (Async)",
                        rewrite_attempt + 1, max_rewrites, ctx.chapter_id)
            emit_progress("rewriter", "running",
                          {"attempt": rewrite_attempt + 1, "risk_level": "高"}, ctx.chapter_id)

            issues = current_audit.get("issues", [])
            plan_issues = [i for i in issues if isinstance(i, dict) and i.get("issue_layer") == "plan"]
            
            final_text, current_audit, ctx = await self._arewrite_iteration(
                ctx, final_text, plan_issues, issues, state_text, rewrite_attempt
            )

        return final_text, current_audit, ctx

    async def _ahandle_plan_rewrite(
        self, ctx: ChapterContext, plan_issues: List[Any], attempt: int
    ) -> Tuple[str, ChapterContext]:
        logger.info("Found %d plan-level issues, re-planning chapter (Async)", len(plan_issues))
        ctx = dataclasses.replace(
            ctx,
            warnings=ctx.warnings + (f"Plan-level issues detected (attempt {attempt+1}). Re-planning chapter.",)
        )
        if hasattr(self.orchestrator.planner, "acreate_plan"):
            new_plan = await self.orchestrator.planner.acreate_plan(ctx.chapter_id, ctx.chapter_goal, must_fix=plan_issues)
        else:
            new_plan = self.orchestrator.planner.create_plan(ctx.chapter_id, ctx.chapter_goal, must_fix=plan_issues)
        
        self.orchestrator._write_json(ctx.chapter_dir / "plan.json", new_plan)
        temp_ctx = dataclasses.replace(ctx, plan=new_plan)
        
        if hasattr(self.orchestrator.generation_phase, "aexecute"):
            temp_ctx = await self.orchestrator.generation_phase.aexecute(temp_ctx)
        else:
            temp_ctx = self.orchestrator.generation_phase.execute(temp_ctx)
        
        return temp_ctx.final_text, dataclasses.replace(ctx, warnings=temp_ctx.warnings)

    async def _ahandle_paragraph_rewrite(
        self, ctx: ChapterContext, final_text: str, text_issues: List[Any], issues: List[Any], attempt: int
    ) -> Tuple[str, ChapterContext]:
        import re
        rebuilt_any = False
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', final_text) if p.strip()]
        
        for issue in text_issues:
            target_text = issue.get("target_text")
            if not target_text:
                continue
                
            target_p, target_idx = find_best_paragraph_match(paragraphs, target_text)
                    
            if target_p:
                prev_p = paragraphs[target_idx - 1] if target_idx > 0 else ""
                next_p = paragraphs[target_idx + 1] if target_idx < len(paragraphs) - 1 else ""
                
                desc_text = str(issue.get("why", "")) + str(issue.get("fix", ""))
                is_stitch_issue = any(k in desc_text for k in ["接缝", "缝合", "过渡", "转场", "Stitch", "scene boundary"])
                
                try:
                    if is_stitch_issue:
                        logger.info("Stitch-related issue detected. Routing rewrite to Stitch Editor (Async).")
                        prompt = (
                            "你是一个极其专业的小说接缝缝合和过渡编辑。请在维持剧情完全一致的前提下，"
                            "消除【待修改段落】及其与前后文接续处的突兀感、拼凑感和断裂感，使过渡极为顺滑自然。\n\n"
                            f"【前文参考】\n{prev_p or '（无）'}\n\n"
                            f"【待修改段落】\n{target_p}\n\n"
                            f"【后文参考】\n{next_p or '（无）'}\n\n"
                            f"【发现的问题】\n{issue.get('why', '转场过渡突兀')}\n\n"
                            "【要求】\n只输出修改后的、用于替换【待修改段落】的新段落正文，不要有任何修饰说明。"
                        ).strip()
                        if hasattr(self.orchestrator.stitch_editor, "aedit"):
                            new_p = await self.orchestrator.stitch_editor.aedit(prompt)
                        else:
                            new_p = self.orchestrator.stitch_editor.edit(prompt)
                    else:
                        prompt = (
                            "你是一个极其专业的小说文笔润色和修订编辑。请在维持原著剧情脉络和上下文极其连贯的前提下，"
                            "对给定的【待修改段落】进行精准局部修正，消除其中的问题。\n\n"
                            f"【前文参考】\n{prev_p or '（无）'}\n\n"
                            f"【待修改段落】\n{target_p}\n\n"
                            f"【后文参考】\n{next_p or '（无）'}\n\n"
                            f"【发现的问题】\n{issue.get('why', '文风或AI腔问题')}\n\n"
                            f"【修改指令】\n{issue.get('fix', '优化修饰')}\n\n"
                            "【极其重要的输出要求】\n"
                            "请只输出你修改后的、用于替换【待修改段落】的新段落正文。不要输出前文和后文，"
                            "不要添加任何多余的引言、Markdown 标记、小标题或修饰说明，只输出这一个新段落的文本。"
                        ).strip()
                        if hasattr(self.orchestrator.style_editor, "aedit"):
                            new_p = await self.orchestrator.style_editor.aedit(prompt)
                        else:
                            new_p = self.orchestrator.style_editor.edit(prompt)
                        
                    new_p = new_p.strip("` \n")
                    if new_p.startswith("```"):
                        lines = new_p.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        new_p = "\n".join(lines).strip()
                    
                    paragraphs[target_idx] = new_p
                    rebuilt_any = True
                except Exception as exc:
                    logger.error("Smart Rewrite paragraph refinement failed: %s", exc)
                    ctx = dataclasses.replace(
                        ctx, warnings=ctx.warnings + (f"Paragraph refinement failed for '{target_text[:15]}': {exc}.",)
                    )
        
        if rebuilt_any:
            final_text = "\n\n".join(paragraphs)
        else:
            logger.info("Smart Rewrite (Async): no specific target paragraph found, falling back to full-chapter style edit")
            issues_summary = json.dumps(issues, ensure_ascii=False)
            feedback_prompt = f"{final_text}\n\n## 审计问题（需修正）\n{issues_summary}"
            try:
                if hasattr(self.orchestrator.style_editor, "aedit"):
                    final_text = await self.orchestrator.style_editor.aedit(feedback_prompt)
                else:
                    final_text = self.orchestrator.style_editor.edit(feedback_prompt)
            except Exception as exc:
                logger.error("Rewrite style edit failed: %s", exc)
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Rewrite style edit failed (attempt {attempt+1}): {exc}.",))
        return final_text, ctx

    async def _arewrite_iteration(
        self,
        ctx: ChapterContext,
        final_text: str,
        plan_issues: List[Any],
        issues: List[Any],
        state_text: str,
        attempt: int
    ) -> Tuple[str, Dict[str, Any], ChapterContext]:
        """Perform a single iteration of rewrite and re-auditing asynchronously."""
        if plan_issues:
            final_text, ctx = await self._ahandle_plan_rewrite(ctx, plan_issues, attempt)
        else:
            text_issues = [i for i in issues if isinstance(i, dict) and i.get("issue_layer") == "text"]
            final_text, ctx = await self._ahandle_paragraph_rewrite(ctx, final_text, text_issues, issues, attempt)

        ctx = dataclasses.replace(ctx, final_text=final_text)
        wc = self._run_wordcount(ctx)
        ctx = dataclasses.replace(ctx, wordcount=wc)
        if should_length_fix_after_audit_rewrite(issues, wc):
            target = ctx.plan.get("target_chars", [1200, 2200]) if ctx.plan else [1200, 2200]
            try:
                if hasattr(self.orchestrator.length_fix, "aadjust"):
                    final_text = await self.orchestrator.length_fix.aadjust(final_text, target)
                else:
                    final_text = self.orchestrator.length_fix.adjust(final_text, target)
                ctx = dataclasses.replace(ctx, final_text=final_text, wordcount=self._run_wordcount(ctx))
            except Exception as exc:
                logger.error("Rewrite length fix adjustment failed: %s", exc)
                ctx = dataclasses.replace(
                    ctx,
                    warnings=ctx.warnings + (f"Rewrite length fix failed (attempt {attempt+1}): {exc}.",),
                )

        # 3. 重新检查一致性与重新审计
        try:
            if hasattr(self.orchestrator.continuity_checker, "acheck"):
                cont_report = await self.orchestrator.continuity_checker.acheck(final_text, state_text)
            else:
                cont_report = self.orchestrator.continuity_checker.check(final_text, state_text)
            self.orchestrator._write_json(ctx.reports_dir / "continuity.json", cont_report)
        except Exception as exc:
            logger.error("Rewrite continuity check failed: %s", exc)
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Rewrite continuity check failed (attempt {attempt+1}): {exc}.",))

        new_audit = {"risk_level": "低", "issues": [], "state_update": {}}
        try:
            state, target_chars, sensitive_words, plan = self._get_audit_args(ctx)
            if hasattr(self.orchestrator.auditor, "aaudit"):
                new_audit = await self.orchestrator.auditor.aaudit(
                    final_text, state=state, target_chars=target_chars, sensitive_words=sensitive_words, plan=plan
                )
            else:
                new_audit = self.orchestrator.auditor.audit(
                    final_text, state=state, target_chars=target_chars, sensitive_words=sensitive_words, plan=plan
                )
            validate_audit_report(new_audit)
        except Exception as exc:
            logger.error("Rewrite audit failed: %s", exc)
            ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Rewrite audit failed (attempt {attempt+1}): {exc}.",))
            
        self._persist_audit_report(ctx, new_audit)
        self.orchestrator._write_json(ctx.chapter_dir / "state_update.json", new_audit.get("state_update", {}))

        emit_progress("rewriter", "done", {
            "attempt": attempt + 1,
            "risk_level": new_audit.get("risk_level", "unknown"),
            "strategy": "plan" if plan_issues else "text"
        }, ctx.chapter_id)

        return final_text, new_audit, ctx


    def _run_continuity_and_summary(self, ctx: ChapterContext, state_text: str) -> Tuple[str, ChapterContext]:
        """Step 6+8: Run continuity check and chapter summary in parallel."""
        emit_progress("continuity_checker", "running", chapter_id=ctx.chapter_id)
        emit_progress("chapter_summary", "running", chapter_id=ctx.chapter_id)
        
        with ThreadPoolExecutor(max_workers=2) as parallel_exec:
            cont_future = parallel_exec.submit(
                self.orchestrator.continuity_checker.check, ctx.final_text, state_text
            )
            summ_future = parallel_exec.submit(
                self.orchestrator.chapter_summary_agent.summarize, ctx.final_text
            )
            try:
                cont_report = cont_future.result(timeout=300)
            except Exception as exc:
                logger.error("Continuity check failed: %s", exc)
                cont_report = {"pass": False, "issues": [{"type": "error", "detail": str(exc)}]}
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Continuity check failed: {exc}.",))
            try:
                ch_summary = summ_future.result(timeout=300)
            except Exception as exc:
                logger.error("Chapter summary failed: %s", exc)
                ch_summary = f"章节总结生成失败: {exc}"
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"Chapter summary failed: {exc}.",))

        self.orchestrator._write_json(ctx.reports_dir / "continuity.json", cont_report)
        emit_progress("continuity_checker", "done", {"pass": cont_report.get("pass", False)}, ctx.chapter_id)
        
        (ctx.chapter_dir / "chapter_summary.md").write_text(ch_summary, encoding="utf-8")
        emit_progress("chapter_summary", "done", chapter_id=ctx.chapter_id)
        return ch_summary, ctx

    def _run_wordcount(self, ctx: ChapterContext) -> Dict[str, Any]:
        """Step 9: Calculate word count and report."""
        target = ctx.plan.get("target_chars", [1200, 2200]) if ctx.plan else [1200, 2200]
        wc = wordcount_report(ctx.final_text, target[0], target[1])
        self.orchestrator._write_json(ctx.reports_dir / "wordcount.json", wc)
        return wc

    def _run_audit_and_extraction(self, ctx: ChapterContext, summary: str) -> Tuple[Dict[str, Any], Dict[str, Any], ChapterContext]:
        """Step 10a+10b: Audit prose and extract state in parallel."""
        emit_progress("auditor", "running", chapter_id=ctx.chapter_id)
        emit_progress("state_extractor", "running", chapter_id=ctx.chapter_id)
        
        state, target_chars, sensitive_words, plan = self._get_audit_args(ctx)
        with ThreadPoolExecutor(max_workers=2) as parallel_exec:
            audit_future = parallel_exec.submit(
                self.orchestrator.auditor.audit,
                ctx.final_text,
                state=state,
                target_chars=target_chars,
                sensitive_words=sensitive_words,
                plan=plan
            )
            state_future = parallel_exec.submit(
                self.orchestrator.state_extractor.extract, ctx.final_text, ctx.chapter_id, summary
            )
            try:
                audit = audit_future.result(timeout=300)
                validate_audit_report(audit)
            except Exception as exc:
                logger.warning("Audit failed or invalid: %s", exc)
                audit = {"risk_level": "低", "issues": [], "state_update": {}}
                ctx = dataclasses.replace(
                    ctx,
                    warnings=ctx.warnings + (f"Audit agent failed or output invalid: {exc}. Fallback to low-risk audit schema.",)
                )
            try:
                ext_state = state_future.result(timeout=300)
            except Exception as exc:
                logger.error("State extraction failed: %s", exc)
                ext_state = {"events": [], "characters": {}, "objects": [], "threads": []}
                ctx = dataclasses.replace(ctx, warnings=ctx.warnings + (f"State extraction failed: {exc}.",))

        self._persist_audit_report(ctx, audit)
        self.orchestrator._write_json(ctx.chapter_dir / "state_update.json", ext_state)
        
        emit_progress("auditor", "done", {"risk_level": audit.get("risk_level", "unknown")}, ctx.chapter_id)
        emit_progress("state_extractor", "done", {"events": len(ext_state.get("events", []))}, ctx.chapter_id)
        return audit, ext_state, ctx

