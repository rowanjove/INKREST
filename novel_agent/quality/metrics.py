"""Local quality metrics and baseline aggregation.

Metrics are diagnostic summaries over persisted chapter reports and explicit
candidate feedback.  They are never used as an AI-detector score or as an
implicit generation gate.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .calibration import DEFAULT_MINIMUM_SAMPLES, load_calibration_report
from .candidate_set import list_candidate_feedback, load_candidate_set


METRICS_SCHEMA_VERSION = 1
BASELINE_FILENAME = "quality_baseline.json"


def baseline_path(root_dir: Path) -> Path:
    return Path(root_dir) / "workspace" / "reports" / BASELINE_FILENAME


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _findings(check: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    value = check.get("findings")
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _parse_time(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _event_in_window(event: Mapping[str, Any], *, since: Optional[datetime], until: Optional[datetime]) -> bool:
    timestamp = _parse_time(event.get("recorded_at") or event.get("updated_at") or event.get("created_at"))
    if timestamp is None:
        return True
    if since and timestamp < since:
        return False
    if until and timestamp > until:
        return False
    return True


def _chapter_row(
    root_dir: Path,
    reports_dir: Path,
    chapter_id: str,
    *,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    quality = _read_json(reports_dir / "quality.json")
    audit = _read_json(reports_dir / "audit.json")
    checks = quality.get("checks") if isinstance(quality.get("checks"), Mapping) else {}
    event_check = checks.get("event_consistency") if isinstance(checks.get("event_consistency"), Mapping) else {}
    expression_check = checks.get("expression_repetition") if isinstance(checks.get("expression_repetition"), Mapping) else {}
    feedback = [
        item
        for item in list_candidate_feedback(root_dir, chapter_id)
        if _event_in_window(item, since=since, until=until)
    ]
    accepts = sum(1 for item in feedback if str(item.get("kind") or item.get("type") or "").lower() in {"accept", "adopt"})
    edits = sum(1 for item in feedback if str(item.get("kind") or item.get("type") or "").lower() == "edit")
    deletes = sum(1 for item in feedback if str(item.get("kind") or item.get("type") or "").lower() in {"delete", "reject"})
    pairwise = sum(1 for item in feedback if str(item.get("kind") or item.get("type") or "").lower() == "pairwise")
    false_positives = sum(1 for item in feedback if str(item.get("kind") or item.get("type") or "").lower() == "false_positive")
    candidate_set = load_candidate_set(root_dir, chapter_id) or {}
    candidate_items = list(candidate_set.get("candidates") or []) + list(candidate_set.get("rejected_candidates") or [])
    cost_units = sum(
        int(item.get("cost_units") or 0)
        for item in candidate_items
        if isinstance(item, Mapping)
    )
    quality_errors = sum(1 for check in checks.values() if isinstance(check, Mapping) and check.get("status") in {"error", "incomplete"})
    rewrite_rounds = len(list(reports_dir.glob("quality_rewrite_candidate*.json")))
    from novel_agent.quality.decision import derive_quality_decision

    decision = derive_quality_decision(quality) if quality else {}
    return {
        "chapter_id": chapter_id,
        "has_quality_report": bool(quality),
        "quality_pass": decision.get("status") in {"pass", "review"} if quality else None,
        "quality_status": decision.get("status") if quality else None,
        "quality_score": quality.get("overall_score"),
        "quality_error": quality_errors,
        "incomplete": bool(quality.get("incomplete")) if quality else False,
        "fact_conflicts": sum(1 for item in _findings(event_check) if "conflict" in str(item.get("type") or item.get("rule_id") or "").lower()),
        "knowledge_boundary_findings": sum(1 for item in _findings(event_check) if "knowledge" in str(item.get("type") or item.get("rule_id") or "").lower()),
        "event_findings": len(_findings(event_check)),
        "expression_repetitions": len(_findings(expression_check)),
        "rewrite_rounds": rewrite_rounds,
        "candidate_feedback": len(feedback),
        "pairwise_count": pairwise,
        "candidate_accepts": accepts,
        "candidate_edits": edits,
        "candidate_deletes": deletes,
        "candidate_false_positives": false_positives,
        "candidate_cost_units": cost_units,
        "audit_status": str(audit.get("status") or "missing"),
        "audit_error": 1 if audit.get("status") in {"error", "incomplete"} or audit.get("error") else 0,
    }


def build_quality_metrics(
    root_dir: Path,
    *,
    minimum_samples: int = DEFAULT_MINIMUM_SAMPLES,
    chapter_id: str = "",
    since: Any = None,
    until: Any = None,
) -> Dict[str, Any]:
    root = Path(root_dir)
    chapters_root = root / "workspace" / "chapters"
    rows: List[Dict[str, Any]] = []
    requested_chapter_id = str(chapter_id or "")
    since_time = _parse_time(since)
    until_time = _parse_time(until)
    if chapters_root.is_dir():
        for chapter_dir in sorted(chapters_root.glob("chapter_*/reports")):
            current_chapter_id = chapter_dir.parent.name.removeprefix("chapter_")
            if requested_chapter_id and current_chapter_id != requested_chapter_id:
                continue
            if (chapter_dir / "quality.json").is_file() or (chapter_dir / "audit.json").is_file():
                if since_time or until_time:
                    try:
                        modified = datetime.fromtimestamp((chapter_dir / "quality.json").stat().st_mtime, tz=timezone.utc)
                    except OSError:
                        modified = None
                    if modified and since_time and modified < since_time:
                        continue
                    if modified and until_time and modified > until_time:
                        continue
                rows.append(_chapter_row(root, chapter_dir, current_chapter_id, since=since_time, until=until_time))
    report_count = sum(1 for row in rows if row["has_quality_report"])
    passed = sum(1 for row in rows if row["quality_pass"] is True)
    feedback_total = sum(int(row["candidate_feedback"]) for row in rows)
    accepts = sum(int(row["candidate_accepts"]) for row in rows)
    edits = sum(int(row["candidate_edits"]) for row in rows)
    decisions = accepts + edits + sum(int(row["candidate_deletes"]) for row in rows)
    calibration = load_calibration_report(root)
    calibration_false_positives = int((calibration.get("feedback_counts") or {}).get("false_positive", 0))
    sample_count = len(rows)
    minimum = max(1, int(minimum_samples))
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": "calibrated" if sample_count >= minimum else "uncalibrated",
        "sample_count": sample_count,
        "minimum_samples": minimum,
        "calibration_status": calibration.get("status", "uncalibrated"),
        "updated_at": _iso_now(),
        "aggregate": {
            "chapter_count": sample_count,
            "quality_report_count": report_count,
            "quality_pass_rate": round(passed / report_count, 4) if report_count else None,
            "fact_conflict_count": sum(int(row["fact_conflicts"]) for row in rows),
            "knowledge_boundary_count": sum(int(row["knowledge_boundary_findings"]) for row in rows),
            "expression_repetition_count": sum(int(row["expression_repetitions"]) for row in rows),
            "rewrite_rounds": sum(int(row["rewrite_rounds"]) for row in rows),
            "quality_error_count": sum(int(row["quality_error"]) for row in rows),
            "audit_error_count": sum(int(row["audit_error"]) for row in rows),
            "candidate_feedback_count": feedback_total,
            "pairwise_count": sum(int(row["pairwise_count"]) for row in rows),
            "candidate_accept_rate": round(accepts / decisions, 4) if decisions else None,
            "candidate_edit_ratio": round(edits / accepts, 4) if accepts else None,
            "candidate_false_positive_count": sum(int(row["candidate_false_positives"]) for row in rows),
            "false_positive_rate": round(
                (sum(int(row["candidate_false_positives"]) for row in rows) + calibration_false_positives)
                / max(1, feedback_total + calibration_false_positives),
                4,
            ),
            "candidate_cost_units": sum(int(row["candidate_cost_units"]) for row in rows),
            "calibration_false_positive_count": calibration_false_positives,
        },
        "rows": rows,
    }


def save_quality_baseline(root_dir: Path, *, minimum_samples: int = DEFAULT_MINIMUM_SAMPLES) -> Dict[str, Any]:
    payload = build_quality_metrics(root_dir, minimum_samples=minimum_samples)
    path = baseline_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return payload


def load_quality_baseline(root_dir: Path) -> Dict[str, Any]:
    payload = _read_json(baseline_path(root_dir))
    if payload.get("schema_version") != METRICS_SCHEMA_VERSION:
        return build_quality_metrics(root_dir)
    return payload


def metrics_csv(payload: Mapping[str, Any]) -> str:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    fields = [
        "chapter_id",
        "quality_pass",
        "quality_score",
        "fact_conflicts",
        "knowledge_boundary_findings",
        "expression_repetitions",
        "rewrite_rounds",
        "candidate_feedback",
        "pairwise_count",
        "candidate_accepts",
        "candidate_edits",
        "candidate_deletes",
        "candidate_false_positives",
        "candidate_cost_units",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fields})
    return output.getvalue()


__all__ = [
    "BASELINE_FILENAME",
    "METRICS_SCHEMA_VERSION",
    "baseline_path",
    "build_quality_metrics",
    "load_quality_baseline",
    "metrics_csv",
    "save_quality_baseline",
]
