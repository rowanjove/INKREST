"""Unified review gate: LLM audit + physical quality guards + optional rewrite."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress
from novel_agent.quality.audit_rewrite import audit_requires_rewrite
from novel_agent.quality.quality_rewrite import attempt_quality_rewrite, build_quality_rewrite_hints
from novel_agent.quality.settings import (
    format_quality_block_message,
    quality_gate_blocks,
    resolve_quality_auto_rewrite,
    resolve_quality_mode,
)
from novel_agent.scripts.count_chars import wordcount_report

if TYPE_CHECKING:
    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.phases.base import ChapterContext

logger = get_logger("services.unified_gate")


def persist_chapter_final_text(chapter_dir: Path, text: str) -> Path:
    """Write accepted/rewritten chapter text to the on-disk projection."""
    path = Path(chapter_dir) / "chapter_final.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")
    return path


def apply_compliance_patches(orchestrator: "NovelOrchestrator", ctx: "ChapterContext") -> "ChapterContext":
    """Deterministically patch sensitive-word hits before LLM rewrite."""
    from novel_agent.scripts.sensitive_scan import (
        apply_sensitive_word_patches,
        load_sensitive_replacements,
        load_sensitive_words,
    )

    root = Path(orchestrator.root_dir)
    words = load_sensitive_words(root / "assets" / "sensitive_words.txt")
    for issue in (ctx.audit or {}).get("issues") or []:
        if isinstance(issue, dict) and issue.get("type") == "sensitive_word_hit":
            hit = str(issue.get("target_text") or "").strip()
            if hit and hit not in words:
                words.append(hit)
    replacements = load_sensitive_replacements(root / "assets" / "sensitive_replacements.json")
    patched = apply_sensitive_word_patches(ctx.final_text or "", words, replacements)
    if patched == (ctx.final_text or ""):
        return ctx
    persist_chapter_final_text(ctx.chapter_dir, patched)
    return dataclasses.replace(ctx, final_text=patched)


async def refresh_audit_after_patch(
    orchestrator: "NovelOrchestrator",
    ctx: "ChapterContext",
) -> tuple[dict, "ChapterContext"]:
    """Re-run hard rules and a single auditor pass after text patches."""
    from novel_agent.quality.audit_persist import split_audit_for_persist
    from novel_agent.quality.audit_schema import validate_audit_report
    from novel_agent.quality.hard_rules import run_hard_rule_audit
    from novel_agent.scripts.sensitive_scan import load_sensitive_words

    state: Dict[str, Any] = {}
    try:
        state = orchestrator.state_manager.get_state() or {}
    except Exception:
        state = {}
    plan = ctx.plan or {}
    target = plan.get("target_chars") or [1200, 2200]
    if not (isinstance(target, (list, tuple)) and len(target) >= 2):
        target = [1200, 2200]
    words = load_sensitive_words(Path(orchestrator.root_dir) / "assets" / "sensitive_words.txt")
    hard_issues = run_hard_rule_audit(
        ctx.final_text or "",
        state,
        [int(target[0]), int(target[1])],
        words,
        ctx.extracted_state or {},
        plan,
    )

    audit = dict(ctx.audit or {})
    auditor = getattr(orchestrator, "auditor", None)
    used_fresh = False
    try:
        if auditor is not None:
            kwargs = {
                "state": state,
                "target_chars": [int(target[0]), int(target[1])],
                "sensitive_words": words,
                "plan": plan,
            }
            if hasattr(auditor, "aaudit"):
                fresh = await auditor.aaudit(ctx.final_text or "", **kwargs)
            else:
                fresh = auditor.audit(ctx.final_text or "", **kwargs)
            if isinstance(fresh, dict):
                validate_audit_report(fresh)
                status = str(fresh.get("status") or "ok").strip().lower()
                if status not in {"error", "incomplete", "unknown"}:
                    audit = fresh
                    used_fresh = True
    except Exception as exc:
        logger.warning("Audit refresh after patch failed: %s", exc)

    if not used_fresh:
        kept = [
            item
            for item in (audit.get("issues") or [])
            if not (
                isinstance(item, dict)
                and str(item.get("type") or "") in {"sensitive_word_hit", "word_count_out_of_bounds"}
            )
        ]
        audit["issues"] = kept + list(hard_issues)
        if not any(
            isinstance(item, dict) and item.get("type") == "sensitive_word_hit"
            for item in audit["issues"]
        ) and str(audit.get("risk_level") or "") in {"高", "high"}:
            audit["risk_level"] = "中"

    public, _ = split_audit_for_persist(audit)
    writer = getattr(orchestrator, "_write_json", None)
    if callable(writer):
        writer(ctx.reports_dir / "audit.json", public)
    else:
        (ctx.reports_dir / "audit.json").write_text(
            json.dumps(public, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return audit, dataclasses.replace(ctx, audit=audit)


def _audit_is_incomplete(audit: Dict[str, Any]) -> bool:
    status = str((audit or {}).get("status") or "ok").strip().lower()
    return status in {"error", "incomplete", "unknown"}


@dataclass
class UnifiedGateOutcome:
    passed: bool
    blocked: bool
    block_message: str
    quality_report: Dict[str, Any]
    ctx: "ChapterContext"
    audit_rewrite_recommended: bool = False


def build_unified_gate_report(
    quality_report: Dict[str, Any],
    audit: Optional[Dict[str, Any]],
    *,
    root_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    audit = audit or {}
    guard = quality_report.get("guard_summary") or {}
    from novel_agent.quality.decision import derive_quality_decision

    decision = derive_quality_decision(quality_report)
    return {
        "overall_pass": decision["status"] in {"pass", "review"},
        "quality_status": decision["status"],
        "hard_gate_pass": decision["hard_gate_pass"],
        "incomplete": bool(quality_report.get("incomplete", False)),
        "quality": {
            "mode": quality_report.get("mode"),
            "overall_pass": quality_report.get("overall_pass"),
            "status": decision["status"],
            "hard_gate_pass": decision["hard_gate_pass"],
            "overall_score": quality_report.get("overall_score"),
            "chapter_score": quality_report.get("chapter_score") or {},
            "guard_status": guard.get("overall_status"),
            "blocked_by": guard.get("blocked_by") or [],
        },
        "audit": {
            "status": audit.get("status", "ok"),
            "risk_level": audit.get("risk_level"),
            "requires_rewrite": audit_requires_rewrite(audit, root_dir=root_dir),
            "issue_count": len(audit.get("issues") or []),
        },
        "rewrite_hints": quality_report.get("rewrite_hints") or "",
    }


def _target_char_range(orchestrator: "NovelOrchestrator") -> List[int]:
    from novel_agent.pipeline import load_pipeline_settings

    chapter_cfg = load_pipeline_settings(orchestrator.root_dir).get("chapter", {}) or {}
    raw = chapter_cfg.get("default_target_chars") or chapter_cfg.get("target_chars") or [2000, 4000]
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return [int(raw[0]), int(raw[1])]
    return [2000, 4000]


def _wordcount_out_of_range(ctx: "ChapterContext", target: List[int]) -> bool:
    wc = ctx.wordcount or {}
    status = str(wc.get("status") or "")
    if status in ("under", "over"):
        return True
    text = (ctx.final_text or "").strip()
    if not text:
        return False
    report = wordcount_report(text, target[0], target[1])
    return report.get("status") != "ok"


def _audit_issues_length_only(audit: Dict[str, Any]) -> bool:
    issues = audit.get("issues") or []
    if not issues:
        return False
    for issue in issues:
        if not isinstance(issue, dict):
            return False
        if str(issue.get("type") or "") != "word_count_out_of_bounds":
            return False
    return True


async def _attempt_auto_length_fix(
    orchestrator: "NovelOrchestrator",
    chapter_id: str,
    ctx: "ChapterContext",
    chapter_dir: Path,
    reports_dir: Path,
) -> "ChapterContext":
    meta_path = reports_dir / "auto_length_fix.json"
    if meta_path.is_file():
        return ctx
    target = _target_char_range(orchestrator)
    if not _wordcount_out_of_range(ctx, target) and not _audit_issues_length_only(ctx.audit or {}):
        return ctx
    text = (ctx.final_text or "").strip()
    if not text:
        return ctx
    emit_progress("length_fix", "running", {"reason": "gate_wordcount"}, chapter_id)
    try:
        if hasattr(orchestrator.length_fix, "aadjust"):
            revised = await orchestrator.length_fix.aadjust(text, target)
        else:
            revised = orchestrator.length_fix.adjust(text, target)
    except Exception as exc:
        logger.warning("Auto length_fix failed for %s: %s", chapter_id, exc)
        emit_progress("length_fix", "error", {"error": str(exc)}, chapter_id)
        return ctx
    if not revised or revised.strip() == text:
        emit_progress("length_fix", "skipped", chapter_id=chapter_id)
        return ctx
    ctx = dataclasses.replace(ctx, final_text=revised)
    persist_chapter_final_text(chapter_dir, revised)
    orchestrator._write_json(
        meta_path,
        {"applied": True, "chars_before": len(text), "chars_after": len(revised)},
    )
    emit_progress("length_fix", "done", chapter_id=chapter_id)
    return ctx


async def run_unified_review_gate(
    orchestrator: "NovelOrchestrator",
    chapter_id: str,
    ctx: "ChapterContext",
    reports_dir: Path,
    chapter_dir: Path,
) -> UnifiedGateOutcome:
    """Run quality guards after audit; optional auto-rewrite; emit unified_gate report."""
    emit_progress("unified_gate", "running", chapter_id=chapter_id)

    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(orchestrator.root_dir).get("runtime", {}) or {}
    if runtime.get("auto_length_fix_on_gate", True):
        ctx = await _attempt_auto_length_fix(
            orchestrator, chapter_id, ctx, chapter_dir, reports_dir
        )
    before_compliance = ctx.final_text or ""
    ctx = apply_compliance_patches(orchestrator, ctx)
    if (ctx.final_text or "") != before_compliance:
        _, ctx = await refresh_audit_after_patch(orchestrator, ctx)

    audit = ctx.audit or {}
    quality_outcome = await orchestrator.chapter_post.write_quality_report(
        chapter_id, ctx.final_text or "", reports_dir, audit=audit
    )
    report = dict(quality_outcome.report)
    report["audit"] = audit
    audit_rewrite = audit_requires_rewrite(audit, root_dir=orchestrator.root_dir)

    if (
        quality_outcome.blocked
        and not _audit_is_incomplete(audit)
        and resolve_quality_auto_rewrite(orchestrator.root_dir)
        and (ctx.final_text or "").strip()
    ):
        revised = await attempt_quality_rewrite(
            orchestrator,
            chapter_id,
            ctx.final_text or "",
            report,
            candidate_path=reports_dir / "quality_rewrite_candidate.txt",
        )
        if revised and revised.strip() != (ctx.final_text or "").strip():
            ctx = dataclasses.replace(ctx, final_text=revised)
            persist_chapter_final_text(chapter_dir, revised)
            from novel_agent.quality.style_precheck import write_style_precheck_cache

            write_style_precheck_cache(reports_dir, revised, orchestrator.root_dir)
            audit, ctx = await refresh_audit_after_patch(orchestrator, ctx)
            quality_outcome = await orchestrator.chapter_post.write_quality_report(
                chapter_id, ctx.final_text or "", reports_dir, audit=audit
            )
            report = dict(quality_outcome.report)
            report["audit"] = audit
            audit_rewrite = audit_requires_rewrite(audit, root_dir=orchestrator.root_dir)

    mode = resolve_quality_mode(orchestrator.root_dir)
    if (
        quality_outcome.blocked
        and runtime.get("auto_length_fix_on_gate", True)
        and not (reports_dir / "auto_length_fix_retry.json").is_file()
    ):
        blocked_only_length = _wordcount_out_of_range(ctx, _target_char_range(orchestrator)) or (
            _audit_issues_length_only(ctx.audit or {})
            and not any(
                str(c.get("level") or "") == "fail"
                for c in (report.get("checks") or {}).values()
                if isinstance(c, dict)
            )
        )
        if blocked_only_length:
            ctx = await _attempt_auto_length_fix(
                orchestrator, chapter_id, ctx, chapter_dir, reports_dir
            )
            orchestrator._write_json(
                reports_dir / "auto_length_fix_retry.json",
                {"retried": True},
            )
            quality_outcome = await orchestrator.chapter_post.write_quality_report(
                chapter_id, ctx.final_text or "", reports_dir, audit=audit
            )
            report = dict(quality_outcome.report)
            from novel_agent.services.chapter_postprocess import QualityReportOutcome

            blocked = quality_gate_blocks(report, mode)
            quality_outcome = QualityReportOutcome(
                report=report,
                blocked=blocked,
                block_message=format_quality_block_message(report) if blocked else "",
            )

    if not (report.get("rewrite_hints") or "").strip():
        hints = build_quality_rewrite_hints(report)
        if hints.strip():
            report["rewrite_hints"] = hints
    if audit_rewrite:
        audit_hint = _audit_rewrite_hint_line(audit)
        if audit_hint:
            merged = (report.get("rewrite_hints") or "").strip()
            report["rewrite_hints"] = f"{merged}\n{audit_hint}".strip() if merged else audit_hint

    unified_doc = build_unified_gate_report(report, audit, root_dir=orchestrator.root_dir)
    unified_doc["blocked"] = quality_outcome.blocked
    unified_doc["resumable_from"] = "audit" if quality_outcome.blocked else None
    orchestrator._write_json(reports_dir / "unified_gate.json", unified_doc)

    passed = not quality_outcome.blocked
    block_message = quality_outcome.block_message if quality_outcome.blocked else ""

    status = "blocked" if not passed else "done"
    emit_progress(
        "unified_gate",
        status,
        {
            "overall_pass": passed,
            "quality_mode": report.get("mode"),
            "audit_requires_rewrite": audit_rewrite,
        },
        chapter_id,
    )

    if not passed and not block_message:
        block_message = format_quality_block_message(report)

    if (ctx.final_text or "").strip():
        persist_chapter_final_text(chapter_dir, ctx.final_text or "")

    return UnifiedGateOutcome(
        passed=passed,
        blocked=not passed,
        block_message=block_message,
        quality_report=report,
        ctx=ctx,
        audit_rewrite_recommended=audit_rewrite,
    )


def _audit_rewrite_hint_line(audit: Dict[str, Any]) -> str:
    risk = str(audit.get("risk_level") or "")
    issues = audit.get("issues") or []
    parts = [f"- [审校/{risk}] 需定向重写"]
    for issue in issues[:3]:
        if isinstance(issue, dict):
            parts.append(f"  - {issue.get('text') or issue.get('type', '')}")
    return "\n".join(parts)
