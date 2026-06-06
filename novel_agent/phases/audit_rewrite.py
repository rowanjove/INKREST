"""Audit-phase rewrite loop helpers (extracted from audit.py)."""

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from novel_agent.logging_config import get_logger
from novel_agent.phases.audit_matching import find_best_paragraph_match
from novel_agent.phases.base import ChapterContext
from novel_agent.progress import emit_progress
from novel_agent.quality.audit_rewrite import audit_requires_rewrite
from novel_agent.quality.generation_policy import should_length_fix_after_audit_rewrite
from novel_agent.quality.audit_schema import validate_audit_report

if TYPE_CHECKING:
    from novel_agent.phases.audit import AuditPhase

logger = get_logger("audit_phase.rewrite")


class AuditRewriteMixin:
    """Rewrite loop methods mixed into AuditPhase."""

    def _run_rewrite_loop(
        self: "AuditPhase",
        ctx: ChapterContext,
        audit: Dict[str, Any],
        ext_state: Dict[str, Any],
        wc: Dict[str, Any],
        summary: str,
        state_text: str,
    ) -> Tuple[str, Dict[str, Any], ChapterContext]:
        max_rewrites = self._resolve_max_rewrites()
        final_text = ctx.final_text
        current_audit = audit

        for rewrite_attempt in range(max_rewrites):
            if not audit_requires_rewrite(current_audit, root_dir=self.orchestrator.root_dir):
                break

            logger.info(
                "Rewrite attempt %d/%d for chapter %s (risk=高)",
                rewrite_attempt + 1,
                max_rewrites,
                ctx.chapter_id,
            )
            emit_progress(
                "rewriter",
                "running",
                {"attempt": rewrite_attempt + 1, "risk_level": "高"},
                ctx.chapter_id,
            )

            issues = current_audit.get("issues", [])
            plan_issues = [i for i in issues if isinstance(i, dict) and i.get("issue_layer") == "plan"]

            final_text, current_audit, ctx = self._rewrite_iteration(
                ctx, final_text, plan_issues, issues, state_text, rewrite_attempt
            )

        return final_text, current_audit, ctx

    def _handle_plan_rewrite(
        self: "AuditPhase", ctx: ChapterContext, plan_issues: List[Any], attempt: int
    ) -> Tuple[str, ChapterContext]:
        logger.info("Found %d plan-level issues, re-planning chapter", len(plan_issues))
        ctx = dataclasses.replace(
            ctx,
            warnings=ctx.warnings
            + (f"Plan-level issues detected (attempt {attempt+1}). Re-planning chapter.",),
        )
        new_plan = self.orchestrator.planner.create_plan(
            ctx.chapter_id, ctx.chapter_goal, must_fix=plan_issues
        )
        self.orchestrator._write_json(ctx.chapter_dir / "plan.json", new_plan)
        temp_ctx = dataclasses.replace(ctx, plan=new_plan)
        temp_ctx = self.orchestrator.generation_phase.execute(temp_ctx)
        return temp_ctx.final_text, dataclasses.replace(ctx, warnings=temp_ctx.warnings)

    def _handle_paragraph_rewrite(
        self: "AuditPhase",
        ctx: ChapterContext,
        final_text: str,
        text_issues: List[Any],
        issues: List[Any],
        attempt: int,
    ) -> Tuple[str, ChapterContext]:
        import re

        rebuilt_any = False
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", final_text) if p.strip()]

        for issue in text_issues:
            target_text = issue.get("target_text")
            if not target_text:
                continue

            target_p, target_idx = find_best_paragraph_match(paragraphs, target_text)

            if target_p:
                prev_p = paragraphs[target_idx - 1] if target_idx > 0 else ""
                next_p = paragraphs[target_idx + 1] if target_idx < len(paragraphs) - 1 else ""

                desc_text = str(issue.get("why", "")) + str(issue.get("fix", ""))
                is_stitch_issue = any(
                    k in desc_text for k in ["接缝", "缝合", "过渡", "转场", "Stitch", "scene boundary"]
                )

                try:
                    if is_stitch_issue:
                        logger.info("Stitch-related issue detected. Routing rewrite to Stitch Editor.")
                        prompt = (
                            "你是一个极其专业的小说接缝缝合和过渡编辑。请在维持剧情完全一致的前提下，"
                            "消除【待修改段落】及其与前后文接续处的突兀感、拼凑感和断裂感，使过渡极为顺滑自然。\n\n"
                            f"【前文参考】\n{prev_p or '（无）'}\n\n"
                            f"【待修改段落】\n{target_p}\n\n"
                            f"【后文参考】\n{next_p or '（无）'}\n\n"
                            f"【发现的问题】\n{issue.get('why', '转场过渡突兀')}\n\n"
                            "【要求】\n只输出修改后的、用于替换【待修改段落】的新段落正文，不要有任何修饰说明。"
                        ).strip()
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
                        ctx,
                        warnings=ctx.warnings
                        + (f"Paragraph refinement failed for '{target_text[:15]}': {exc}.",),
                    )

        if rebuilt_any:
            final_text = "\n\n".join(paragraphs)
        else:
            logger.info(
                "Smart Rewrite: no specific target paragraph found, falling back to full-chapter style edit"
            )
            issues_summary = json.dumps(issues, ensure_ascii=False)
            feedback_prompt = f"{final_text}\n\n## 审计问题（需修正）\n{issues_summary}"
            try:
                final_text = self.orchestrator.style_editor.edit(feedback_prompt)
            except Exception as exc:
                logger.error("Rewrite style edit failed: %s", exc)
                ctx = dataclasses.replace(
                    ctx,
                    warnings=ctx.warnings + (f"Rewrite style edit failed (attempt {attempt+1}): {exc}.",),
                )
        return final_text, ctx

    def _rewrite_iteration(
        self: "AuditPhase",
        ctx: ChapterContext,
        final_text: str,
        plan_issues: List[Any],
        issues: List[Any],
        state_text: str,
        attempt: int,
    ) -> Tuple[str, Dict[str, Any], ChapterContext]:
        if plan_issues:
            final_text, ctx = self._handle_plan_rewrite(ctx, plan_issues, attempt)
        else:
            text_issues = [i for i in issues if isinstance(i, dict) and i.get("issue_layer") == "text"]
            final_text, ctx = self._handle_paragraph_rewrite(ctx, final_text, text_issues, issues, attempt)

        ctx = dataclasses.replace(ctx, final_text=final_text)
        wc = self._run_wordcount(ctx)
        ctx = dataclasses.replace(ctx, wordcount=wc)
        if should_length_fix_after_audit_rewrite(issues, wc):
            target = ctx.plan.get("target_chars", [1200, 2200]) if ctx.plan else [1200, 2200]
            try:
                final_text = self.orchestrator.length_fix.adjust(final_text, target)
                ctx = dataclasses.replace(ctx, final_text=final_text, wordcount=self._run_wordcount(ctx))
            except Exception as exc:
                logger.error("Rewrite length fix adjustment failed: %s", exc)
                ctx = dataclasses.replace(
                    ctx,
                    warnings=ctx.warnings + (f"Rewrite length fix failed (attempt {attempt+1}): {exc}.",),
                )

        try:
            cont_report = self.orchestrator.continuity_checker.check(final_text, state_text)
            self.orchestrator._write_json(ctx.reports_dir / "continuity.json", cont_report)
        except Exception as exc:
            logger.error("Rewrite continuity check failed: %s", exc)
            ctx = dataclasses.replace(
                ctx,
                warnings=ctx.warnings + (f"Rewrite continuity check failed (attempt {attempt+1}): {exc}.",),
            )

        new_audit: Dict[str, Any] = {"risk_level": "低", "issues": [], "state_update": {}}
        try:
            state, target_chars, sensitive_words, plan = self._get_audit_args(ctx)
            new_audit = self.orchestrator.auditor.audit(
                final_text,
                state=state,
                target_chars=target_chars,
                sensitive_words=sensitive_words,
                plan=plan,
            )
            validate_audit_report(new_audit)
        except Exception as exc:
            logger.error("Rewrite audit failed: %s", exc)
            ctx = dataclasses.replace(
                ctx,
                warnings=ctx.warnings + (f"Rewrite audit failed (attempt {attempt+1}): {exc}.",),
            )

        self._persist_audit_report(ctx, new_audit)
        self.orchestrator._write_json(ctx.chapter_dir / "state_update.json", new_audit.get("state_update", {}))

        emit_progress(
            "rewriter",
            "done",
            {
                "attempt": attempt + 1,
                "risk_level": new_audit.get("risk_level", "unknown"),
                "strategy": "plan" if plan_issues else "text",
            },
            ctx.chapter_id,
        )

        return final_text, new_audit, ctx