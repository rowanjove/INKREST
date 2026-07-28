"""Normalize quality reports and pipeline alerts into one review queue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from novel_agent.services.pipeline_pending import collect_pipeline_alerts_cached
from novel_agent.services.project_snapshot import build_quality_summary

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
}

RECOMMENDED_ACTIONS = {
    "quality_blocked": "edit_then_gate",
    "approval_rejected": "resume_audit",
    "batch_retry": "rewrite",
    "external_review_pending": "external_review",
    "report_failed": "edit_then_gate",
    "report_invalid": "inspect_report",
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
) -> dict[str, Any]:
    normalized_level = str(level or "fail").lower()
    severity = "error" if normalized_level in {"fail", "error", "blocked"} else "warning"
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
    }


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


def build_quality_review_queue(root_dir: Path) -> dict[str, Any]:
    """Build one review item per chapter without exposing filesystem paths."""
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
            "message": str(alert.get("message") or STAGE_LABELS.get(stage) or "需要处理"),
            "overall_score": None,
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

        guard = report.get("guard_summary")
        guard = guard if isinstance(guard, dict) else {}
        checks = report.get("checks")
        checks = checks if isinstance(checks, dict) else {}
        blocked_by = [
            str(value) for value in guard.get("blocked_by", []) if str(value).strip()
        ]
        failed = (
            report.get("overall_pass") is False
            or str(guard.get("overall_status") or "").upper() == "FAIL"
            or bool(blocked_by)
        )
        if not failed and chapter_id not in items:
            continue
        item = items.setdefault(
            chapter_id,
            {
                "chapter_id": chapter_id,
                "chapter_title": _chapter_title(chapter_dir, chapter_id),
                "stage": "report_failed",
                "stage_label": STAGE_LABELS["report_failed"],
                "severity": "error",
                "message": "质量检查未通过",
                "overall_score": None,
                "issues": [],
                "completed_stages": [],
                "updated_at": None,
                "recommended_action": RECOMMENDED_ACTIONS["report_failed"],
            },
        )
        try:
            item["overall_score"] = int(round(float(report.get("overall_score"))))
        except (TypeError, ValueError):
            item["overall_score"] = None
        for code, raw_check in checks.items():
            if not isinstance(raw_check, dict) or raw_check.get("pass") is not False:
                continue
            _merge_issue(
                item["issues"],
                _issue(
                    str(code),
                    score=raw_check.get("score"),
                    level=raw_check.get("level"),
                    details=raw_check.get("details"),
                ),
            )
        for code in blocked_by:
            _merge_issue(item["issues"], _issue(code))

    ordered = sorted(
        items.values(),
        key=lambda item: (
            item["severity"] != "error",
            str(item["chapter_id"]),
        ),
    )
    quality_summary = build_quality_summary(root)
    stage_counts: dict[str, int] = {}
    for item in ordered:
        stage = str(item["stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    return {
        "summary": {
            **quality_summary,
            "open_items": len(ordered),
            "stage_counts": stage_counts,
        },
        "items": ordered,
    }
