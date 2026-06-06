"""Summarize chapters needing human attention (gate block + batch skip)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from novel_agent.services.batch_retry_queue import list_pending_retries

_PIPELINE_ALERT_STAGES = frozenset({"quality_blocked", "approval_rejected"})


def _scan_checkpoint_alerts(root_dir: Path, *, limit: int = 20) -> List[Dict[str, Any]]:
    chapters_root = root_dir / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return []
    alerts: List[Dict[str, Any]] = []
    for chapter_dir in sorted(chapters_root.glob("chapter_*")):
        checkpoint_path = chapter_dir / "checkpoint.json"
        if not checkpoint_path.is_file():
            continue
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if checkpoint.get("resolved_at"):
            continue
        last_stage = str(checkpoint.get("last_stage") or "")
        if last_stage not in _PIPELINE_ALERT_STAGES:
            continue
        chapter_id = checkpoint.get("chapter_id") or chapter_dir.name.replace("chapter_", "")
        alerts.append(
            {
                "chapter_id": str(chapter_id),
                "last_stage": last_stage,
                "message": last_stage,
            }
        )
        if len(alerts) >= limit:
            break
    return alerts


def summarize_pipeline_pending(root_dir: Path) -> Dict[str, Any]:
    retries = list_pending_retries(root_dir)
    gate_alerts = _scan_checkpoint_alerts(root_dir, limit=50)
    retry_ids = {str(r.get("chapter_id")) for r in retries}
    gate_only = [a for a in gate_alerts if a["chapter_id"] not in retry_ids]
    return {
        "pending_retry_count": len(retries),
        "pending_gate_count": len(gate_only),
        "pending_total": len(retries) + len(gate_only),
        "retries": retries[:10],
        "gate_blocked": gate_only[:10],
    }