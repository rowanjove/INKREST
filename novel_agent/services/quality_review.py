"""Normalize quality reports and pipeline alerts into one review queue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from novel_agent.services.pipeline_pending import collect_pipeline_alerts_cached
from novel_agent.services.project_snapshot import build_quality_summary
from novel_agent.quality.decision import derive_quality_decision

CHECK_LABELS = {
    "continuity_physical": "前后章连续性",
    "style": "文风与表达",
    "anti_ai_flavor": "机械感与套路化",
    "layout": "段落与排版",
    "scene_delta": "场景推进",
    "reference_similarity": "参考文本相似度",
    "ai_flavor": "AI 痕迹风险",
    "quality_report_invalid": "质量报告损坏",
}

STAGE_LABELS = {
    "quality_blocked": "质量阻断",
    "approval_rejected": "审批退回",
    "batch_retry": "批量跳过",
    "external_review_pending": "等待外审",
    "report_failed": "质量未通过",
    "report_invalid": "报告损坏",
    "quality_review": "建议优化",
}

RECOMMENDED_ACTIONS = {
    "quality_blocked": "edit_then_gate",
    "approval_rejected": "resume_audit",
    "batch_retry": "rewrite",
    "external_review_pending": "external_review",
    "report_failed": "edit_then_gate",
    "report_invalid": "inspect_report",
    "quality_review": "optional_edit",
}


def _read_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, False
    return (value, True) if isinstance(value, dict) else ({}, False)


def _chapter_title(chapter_dir: Path, chapter_id: str) -> str:
    plan, readable = _read_json(chapter_dir / "plan.json")
    if readable:
        title = str(plan.get("chapter_title") or plan.get("title") or "").strip()
        if title:
            return title
    return f"第 {chapter_id} 章"


def _normalize_details(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    details: list[str] = []
    for item in value[:20]:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(
                item.get("message")
                or item.get("detail")
                or item.get("reason")
                or ""
            ).strip()
        else:
            text = str(item).strip()
        if text:
            details.append(text[:500])
    return details


def _issue(
    code: str,
    *,
    score: Any = None,
    level: Any = None,
    details: Any = None,
    blocking: bool = False,
    suggestion: str = "",
    location: str = "chapter",
    span: Any = None,
) -> dict[str, Any]:
    normalized_level = str(level or "fail").lower()
    severity = "error" if blocking else "warning"
    try:
        normalized_score = int(round(float(score))) if score is not None else None
    except (TypeError, ValueError):
        normalized_score = None
    return {
        "code": code,
        "label": CHECK_LABELS.get(code, code.replace("_", " ")),
        "severity": severity,
        "score": normalized_score,
        "details": _normalize_details(details),
        "blocking": blocking,
        "suggestion": suggestion or (
            "修改对应正文后重跑门禁。" if blocking else "按证据局部优化；本项不会阻断继续生产。"
        ),
        "location": location or "chapter",
        "span": span,
    }


def quality_issues_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return actionable, explicitly blocking/advisory issues for the UI."""
    guard = report.get("guard_summary")
    guard = guard if isinstance(guard, dict) else {}
    blocked_by = {str(value) for value in guard.get("blocked_by", []) if str(value)}
    checks = report.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    issues: list[dict[str, Any]] = []
    for code, raw_check in checks.items():
        if not isinstance(raw_check, dict):
            continue
        level = str(raw_check.get("level") or "").lower()
        if raw_check.get("pass") is not False and level not in {"warning", "review", "fail", "error"}:
            continue
        findings = raw_check.get("findings")
        findings = findings if isinstance(findings, list) else []
        first = next((item for item in findings if isinstance(item, dict)), {})
        details = list(raw_check.get("details") or []) if isinstance(raw_check.get("details"), list) else []
        for finding in findings:
            if isinstance(finding, dict):
                message = finding.get("message") or finding.get("reason")
                if message and message not in details:
                    details.append(message)
        _merge_issue(
            issues,
            _issue(
                str(code),
                score=raw_check.get("score"),
                level=level,
                details=details,
                blocking=str(code) in blocked_by,
                suggestion=str(first.get("suggestion") or raw_check.get("suggestion") or ""),
                location=str(first.get("location") or raw_check.get("location") or "chapter"),
                span=first.get("span") or first.get("source_span") or raw_check.get("span"),
            ),
        )
    for code in blocked_by:
        if not any(item["code"] == code for item in issues):
            _merge_issue(issues, _issue(code, blocking=True))

    audit = report.get("audit")
    audit = audit if isinstance(audit, dict) else {}
    audit_items = audit.get("issues")
    audit_items = audit_items if isinstance(audit_items, list) else []
    audit_blocking = str(audit.get("status") or "").strip().lower() in {
        "error",
        "incomplete",
        "unknown",
    }
    for index, raw_issue in enumerate(audit_items[:50]):
        if isinstance(raw_issue, dict):
            issue_type = str(
                raw_issue.get("type")
                or raw_issue.get("rule_id")
                or raw_issue.get("code")
                or f"issue_{index + 1}"
            )
            details = [
                str(value)
                for key in ("message", "reason", "why", "detail", "fix")
                if (value := raw_issue.get(key))
            ]
            level = raw_issue.get("severity") or raw_issue.get("level")
            suggestion = str(raw_issue.get("fix") or raw_issue.get("suggestion") or "")
            location = str(raw_issue.get("location") or raw_issue.get("source") or "chapter")
            span = raw_issue.get("span") or raw_issue.get("source_span")
        else:
            issue_type = f"issue_{index + 1}"
            details = [str(raw_issue)] if raw_issue else []
            level = "review"
            suggestion = "根据审校证据人工检查后决定是否优化。"
            location = "chapter"
            span = None
        _merge_issue(
            issues,
            _issue(
                f"audit.{issue_type}",
                level=level,
                details=details,
                blocking=audit_blocking,
                suggestion=suggestion,
                location=location,
                span=span,
            ),
        )
    return issues


def _merge_issue(target: list[dict[str, Any]], issue: dict[str, Any]) -> None:
    existing = next((item for item in target if item["code"] == issue["code"]), None)
    if existing is None:
        target.append(issue)
        return
    if existing.get("score") is None and issue.get("score") is not None:
        existing["score"] = issue["score"]
    existing_details = list(existing.get("details") or [])
    for detail in issue.get("details") or []:
        if detail not in existing_details:
            existing_details.append(detail)
    existing["details"] = existing_details[:20]


def build_quality_review_queue(
    root_dir: Path,
    *,
    cursor: str | None = None,
    limit: int | None = None,
    status_filter: str | None = None,
    severity_filter: str | None = None,
) -> dict[str, Any]:
    """Build review items per chapter with optional cursor-based pagination and filtering."""
    root = Path(root_dir)
    chapters_root = root / "workspace" / "chapters"
    items: dict[str, dict[str, Any]] = {}

    try:
        alerts = collect_pipeline_alerts_cached(root)
    except Exception:
        alerts = []
    for alert in alerts:
        chapter_id = str(alert.get("chapter_id") or "").strip()
        if not chapter_id:
            continue
        chapter_dir = chapters_root / f"chapter_{chapter_id}"
        stage = str(alert.get("last_stage") or "quality_blocked")
        items[chapter_id] = {
            "chapter_id": chapter_id,
            "chapter_title": _chapter_title(chapter_dir, chapter_id),
            "stage": stage,
            "stage_label": STAGE_LABELS.get(stage, "需要处理"),
            "severity": "warning" if stage == "external_review_pending" else "error",
            "blocking": stage not in {"external_review_pending", "quality_review"},
            "message": str(alert.get("message") or STAGE_LABELS.get(stage) or "需要处理"),
            "overall_score": None,
            "chapter_score": None,
            "blocked_by": [],
            "issues": [],
            "completed_stages": [
                str(value) for value in (alert.get("completed_stages") or [])
            ],
            "updated_at": alert.get("timestamp"),
            "recommended_action": RECOMMENDED_ACTIONS.get(stage, "open_writer"),
        }

    report_paths = (
        sorted(chapters_root.glob("chapter_*/reports/quality.json"))
        if chapters_root.is_dir()
        else []
    )
    for report_path in report_paths:
        chapter_dir = report_path.parent.parent
        chapter_id = chapter_dir.name.removeprefix("chapter_")
        report, readable = _read_json(report_path)
        checkpoint, _checkpoint_readable = _read_json(chapter_dir / "checkpoint.json")
        if checkpoint.get("resolved_at") and chapter_id not in items:
            continue
        if not readable:
            item = items.setdefault(
                chapter_id,
                {
                    "chapter_id": chapter_id,
                    "chapter_title": _chapter_title(chapter_dir, chapter_id),
                    "stage": "report_invalid",
                    "stage_label": STAGE_LABELS["report_invalid"],
                    "severity": "error",
                    "message": "质量报告无法读取，需要重新审校",
                    "overall_score": None,
                    "chapter_score": None,
                    "blocked_by": [],
                    "issues": [],
                    "completed_stages": [],
                    "updated_at": None,
                    "recommended_action": RECOMMENDED_ACTIONS["report_invalid"],
                },
            )
            _merge_issue(
                item["issues"],
                _issue(
                    "quality_report_invalid",
                    details=["报告内容无法解析，请重新审校生成新的报告。"],
                ),
            )
            continue

        # A user-level dismissal is persisted on the chapter checkpoint.  Do
        # not recreate a quality queue item from the unchanged quality.json;
        # other independent alerts (for example external review) are retained.
        # Older quality reports only stored an L2 summary while audit.json
        # retained the actual findings.  Merge that source for compatibility
        # before deriving status/issues.
        audit_doc, audit_readable = _read_json(report_path.parent / "audit.json")
        report_audit = report.get("audit")
        report_audit = report_audit if isinstance(report_audit, dict) else {}
        if audit_readable and isinstance(audit_doc.get("issues"), list):
            if not isinstance(report_audit.get("issues"), list):
                report_audit = {**report_audit, "issues": audit_doc["issues"]}
            if not report_audit.get("status") and audit_doc.get("status"):
                report_audit["status"] = audit_doc["status"]
            report = {**report, "audit": report_audit}

        guard = report.get("guard_summary")
        guard = guard if isinstance(guard, dict) else {}
        checks = report.get("checks")
        checks = checks if isinstance(checks, dict) else {}
        blocked_by = [
            str(value) for value in guard.get("blocked_by", []) if str(value).strip()
        ]
        decision = derive_quality_decision(report)
        needs_attention = decision["status"] in {"blocked", "incomplete", "review"}
        if not needs_attention and chapter_id not in items:
            continue
        default_stage = "quality_review" if decision["status"] == "review" else "report_failed"
        item = items.setdefault(
            chapter_id,
            {
                "chapter_id": chapter_id,
                "chapter_title": _chapter_title(chapter_dir, chapter_id),
                "stage": default_stage,
                "stage_label": STAGE_LABELS[default_stage],
                "severity": "warning" if decision["status"] == "review" else "error",
                "message": decision["title"],
                "overall_score": None,
                "chapter_score": None,
                "blocked_by": [],
                "issues": [],
                "completed_stages": [],
                "updated_at": None,
                "recommended_action": RECOMMENDED_ACTIONS[default_stage],
            },
        )
        item["quality_status"] = decision["status"]
        item["hard_gate_pass"] = decision["hard_gate_pass"]
        item["blocking"] = decision["blocking"]
        try:
            item["overall_score"] = int(round(float(report.get("overall_score"))))
        except (TypeError, ValueError):
            item["overall_score"] = None
        chapter_score = report.get("chapter_score")
        if isinstance(chapter_score, dict) and chapter_score.get("score") is not None:
            try:
                item["chapter_score"] = round(float(chapter_score.get("score")), 1)
            except (TypeError, ValueError):
                item["chapter_score"] = item.get("chapter_score")
        if blocked_by:
            item["blocked_by"] = blocked_by
        for issue in quality_issues_from_report(report):
            _merge_issue(item["issues"], issue)

    ordered = sorted(
        items.values(),
        key=lambda item: (
            item["severity"] != "error",
            str(item["chapter_id"]),
        ),
    )
    quality_summary = build_quality_summary(root)
    stage_counts: dict[str, int] = {}
    blocking_items = 0
    advisory_items = 0
    for item in ordered:
        stage = str(item["stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        if item.get("blocking") or str(item.get("severity") or "") == "error":
            blocking_items += 1
        else:
            advisory_items += 1

    filtered_items = ordered
    if severity_filter:
        sev = str(severity_filter).strip().lower()
        filtered_items = [it for it in filtered_items if str(it.get("severity", "")).lower() == sev]
    if status_filter:
        stat = str(status_filter).strip().lower()
        filtered_items = [it for it in filtered_items if str(it.get("stage", "")).lower() == stat]

    total_filtered = len(filtered_items)

    if limit is not None or cursor is not None:
        page_limit = max(1, limit if limit is not None else 50)
        start_idx = 0
        if cursor:
            for i, it in enumerate(filtered_items):
                if str(it.get("chapter_id")) == str(cursor):
                    start_idx = i + 1
                    break
        page_items = filtered_items[start_idx : start_idx + page_limit]
        has_more = (start_idx + page_limit) < total_filtered
        next_cursor = page_items[-1]["chapter_id"] if has_more and page_items else None
    else:
        page_items = filtered_items
        has_more = False
        next_cursor = None

    return {
        "summary": {
            **quality_summary,
            "open_items": len(ordered),
            "blocking_items": blocking_items,
            "advisory_items": advisory_items,
            "stage_counts": stage_counts,
        },
        "items": page_items,
        "next_cursor": next_cursor,
        "total": total_filtered,
        "has_more": has_more,
    }
