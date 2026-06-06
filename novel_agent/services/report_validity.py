"""Mark chapter reports stale when goal/plan changes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.logging_config import get_logger

logger = get_logger("services.report_validity")

STALE_REPORT_FILES = (
    "audit.json",
    "quality.json",
    "unified_gate.json",
    "persona_eval.json",
    "wordcount.json",
    "continuity.json",
)

VALIDITY_MANIFEST = "report_validity.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def invalidate_chapter_reports(
    reports_dir: Path,
    *,
    reason: str,
    goal_hash: str = "",
    plan_hash: str = "",
) -> Dict[str, Any]:
    """Flag on-disk review reports as stale (goal/plan/outline change)."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    touched: List[str] = []
    for name in STALE_REPORT_FILES:
        path = reports_dir / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if not isinstance(data, dict):
            data = {"_raw_stale": True}
        data["stale"] = True
        data["stale_reason"] = reason
        data["stale_at"] = _utc_now()
        if goal_hash:
            data["stale_goal_hash"] = goal_hash
        if plan_hash:
            data["stale_plan_hash"] = plan_hash
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        touched.append(name)

    manifest = {
        "valid": False,
        "reason": reason,
        "invalidated_at": _utc_now(),
        "goal_hash": goal_hash,
        "plan_hash": plan_hash,
        "stale_files": touched,
    }
    (reports_dir / VALIDITY_MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Invalidated %d reports in %s (%s)", len(touched), reports_dir, reason)
    return manifest


def load_report_validity(reports_dir: Path) -> Optional[Dict[str, Any]]:
    path = reports_dir / VALIDITY_MANIFEST
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None