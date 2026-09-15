"""Canonical user-facing decision semantics for chapter quality reports."""

from __future__ import annotations

from typing import Any, Mapping


def derive_quality_decision(report: Mapping[str, Any]) -> dict[str, Any]:
    """Separate hard blocking, audit completeness and advisory review.

    Older reports are accepted: missing fields are derived from guard/check data.
    """
    stored = report.get("quality_decision")
    stored_audit = report.get("audit")
    stored_audit_issues = (
        stored_audit.get("issues")
        if isinstance(stored_audit, Mapping)
        else None
    )
    required_stored_keys = {
        "status",
        "title",
        "message",
        "blocking",
        "hard_gate_pass",
        "audit_complete",
        "keep",
        "blocked_by",
        "next_action",
    }
    guard_preview = report.get("guard_summary")
    guard_preview = guard_preview if isinstance(guard_preview, Mapping) else {}
    stored_conflicts_guard = (
        str(stored.get("status") or "") in {"pass", "review"}
        if isinstance(stored, Mapping)
        else False
    ) and (
        str(guard_preview.get("overall_status") or "").upper() == "FAIL"
        or bool(guard_preview.get("blocked_by"))
    )
    if (
        isinstance(stored, Mapping)
        and required_stored_keys.issubset(stored)
        and str(stored.get("status") or "") in {
            "pass",
            "review",
            "blocked",
            "incomplete",
        }
        and not stored_audit_issues
        and not stored_conflicts_guard
    ):
        return dict(stored)

    guard = report.get("guard_summary")
    guard = guard if isinstance(guard, Mapping) else {}
    blocked_by = [str(item) for item in guard.get("blocked_by", []) if str(item)]
    hard_gate_pass = str(guard.get("overall_status") or "").upper() != "FAIL" and not blocked_by

    audit = report.get("audit")
    audit = audit if isinstance(audit, Mapping) else {}
    audit_status = str(audit.get("status") or "ok").strip().lower()
    audit_issues = audit.get("issues")
    audit_issues = audit_issues if isinstance(audit_issues, list) else []
    incomplete = bool(report.get("incomplete")) or audit_status in {
        "error",
        "incomplete",
        "unknown",
    }

    score = report.get("chapter_score")
    score = score if isinstance(score, Mapping) else {}
    keep = score.get("keep") is not False

    checks = report.get("checks")
    checks = checks if isinstance(checks, Mapping) else {}
    advisory = str(guard.get("overall_status") or "").upper() == "WARN" or any(
        isinstance(check, Mapping)
        and (
            check.get("pass") is False
            or str(check.get("level") or "").lower() in {"warning", "review", "fail"}
        )
        for check in checks.values()
    ) or bool(audit_issues)

    legacy_failure = (
        not guard
        and not score
        and "quality_status" not in report
        and report.get("overall_pass") is False
    )
    if legacy_failure:
        hard_gate_pass = False

    if incomplete:
        status = "incomplete"
        title = "审校未完成"
        message = "审校过程没有完整结束，请先重试审校。"
        next_action = "resume_audit"
    elif legacy_failure or not hard_gate_pass or not keep:
        status = "blocked"
        title = "阻断，必须修复"
        message = "本章存在硬门问题，需要修改正文后重跑门禁。"
        next_action = "edit_then_gate"
    elif advisory:
        status = "review"
        title = "可保留，建议优化"
        message = "本章已通过生产硬门；以下问题是优化建议，不会阻断继续生产。"
        next_action = "optional_edit"
    else:
        status = "pass"
        title = "质量检查通过"
        message = "本章已通过质量检查，可以继续生产。"
        next_action = "none"

    return {
        "status": status,
        "title": title,
        "message": message,
        "blocking": status in {"blocked", "incomplete"},
        "hard_gate_pass": hard_gate_pass,
        "audit_complete": not incomplete,
        "keep": keep,
        "blocked_by": blocked_by,
        "next_action": next_action,
    }


def quality_report_passes(report: Mapping[str, Any]) -> bool:
    """Whether production may retain/continue with this chapter."""
    return derive_quality_decision(report)["status"] in {"pass", "review"}


__all__ = ["derive_quality_decision", "quality_report_passes"]
