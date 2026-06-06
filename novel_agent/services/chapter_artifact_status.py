"""Label on-disk chapter artifacts as authoritative, reference, or stale."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ArtifactRow = Dict[str, Any]

_STATUS_LABELS = {
    "authoritative": "可信",
    "reference": "仅供参考",
    "stale": "可能过期",
    "missing": "缺失",
}

_ARTIFACT_SPECS: List[Tuple[str, str, str, Optional[str]]] = [
    ("plan", "plan.json", "章节计划", "planner"),
    ("final", "chapter_final.txt", "终稿正文", "generation"),
    ("wordcount", "reports/wordcount.json", "字数统计", "generation"),
    ("continuity", "reports/continuity.json", "连续性检查", "generation"),
    ("audit", "reports/audit.json", "安全审校", "audit"),
    ("summary", "chapter_summary.md", "章节总结", "audit"),
    ("quality", "reports/quality.json", "质量报告", "audit"),
    ("unified_gate", "reports/unified_gate.json", "统一门禁", "audit"),
    ("state_update", "state_update.json", "状态落库", "post_audit"),
]


def _file_nonempty(path: Path) -> bool:
    if not path.exists():
        return False
    if path.suffix == ".json":
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return bool(data)
        except (OSError, ValueError):
            return False
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except OSError:
        return False


def _trust_for_blocked(key: str, exists: bool) -> Tuple[str, str]:
    if not exists:
        return "missing", "尚未生成"
    if key in ("quality", "unified_gate"):
        return "authoritative", "质量阻断依据，请以本报告为准"
    if key == "state_update":
        return "stale", "门禁未通过，全局状态未提交"
    if key in ("audit", "summary"):
        return "reference", "检查点已回滚，恢复流水线时将重新审校"
    if key in ("plan", "final", "wordcount", "continuity"):
        return "authoritative", "生成阶段产物，仍可作为定向改写依据"
    return "reference", "阻断后需结合恢复阶段判断是否仍适用"


def _trust_for_approval_rejected(key: str, exists: bool) -> Tuple[str, str]:
    if not exists:
        return "missing", "尚未生成"
    if key == "state_update":
        return "stale", "审批未通过，状态落库未生效"
    if key in ("audit", "summary", "quality", "unified_gate"):
        return "reference", "审批回滚后需重新审校"
    return "authoritative", "生成阶段产物仍有效"


def _trust_default(
    key: str,
    exists: bool,
    stage: Optional[str],
    completed: set,
) -> Tuple[str, str]:
    if not exists:
        return "missing", "尚未生成"
    if stage and stage not in completed:
        return "reference", f"磁盘有缓存，但检查点未标记「{stage}」完成"
    return "authoritative", "与当前检查点一致"


def _report_json_stale(path: Path) -> Tuple[bool, str]:
    if not path.exists() or path.suffix != ".json":
        return False, ""
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, ""
    if isinstance(data, dict) and data.get("stale"):
        return True, str(data.get("stale_reason") or "内容已过期")
    return False, ""


def build_chapter_artifact_status(
    chapter_dir: Path,
    checkpoint: Optional[Dict[str, Any]] = None,
    unified_gate: Optional[Dict[str, Any]] = None,
    report_validity: Optional[Dict[str, Any]] = None,
) -> List[ArtifactRow]:
    checkpoint = checkpoint or {}
    unified_gate = unified_gate or {}
    report_validity = report_validity or {}
    completed = set(checkpoint.get("completed_stages") or [])
    last_stage = str(checkpoint.get("last_stage") or "")
    resumable_from = checkpoint.get("resumable_from") or unified_gate.get("resumable_from")
    reports_invalid = report_validity.get("valid") is False

    rows: List[ArtifactRow] = []
    for key, rel_path, label, stage in _ARTIFACT_SPECS:
        path = chapter_dir / rel_path
        exists = _file_nonempty(path)
        file_stale, stale_reason = _report_json_stale(path)

        if reports_invalid and key in (
            "audit",
            "quality",
            "unified_gate",
            "continuity",
            "wordcount",
        ):
            trust, note = "stale", str(report_validity.get("reason") or "goal/plan 已变更")
        elif file_stale:
            trust, note = "stale", stale_reason
        elif last_stage == "quality_blocked" or unified_gate.get("blocked"):
            trust, note = _trust_for_blocked(key, exists)
        elif last_stage == "approval_rejected":
            trust, note = _trust_for_approval_rejected(key, exists)
        else:
            trust, note = _trust_default(key, exists, stage, completed)

        rows.append(
            {
                "key": key,
                "path": rel_path,
                "label": label,
                "exists": exists,
                "status": trust,
                "status_label": _STATUS_LABELS.get(trust, trust),
                "note": note,
                "pipeline_stage": stage,
            }
        )

    if resumable_from:
        for row in rows:
            row["resumable_from"] = resumable_from

    return rows