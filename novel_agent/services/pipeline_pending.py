"""Summarize chapters needing human attention (gate block + batch skip)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from novel_agent.logging_config import get_logger
from novel_agent.services.batch_retry_queue import list_pending_retries

logger = get_logger("services.pipeline_pending")

_ALERT_COUNT_CACHE_REL = "workspace/reports/pending_alert_count.cache.json"

_CHECKPOINT_ALERT_STAGES = frozenset({"quality_blocked", "approval_rejected"})

_PIPELINE_ALERT_MESSAGES = {
    "quality_blocked": "质量门禁未通过，落库已暂停",
    "approval_rejected": "审批未通过，已回滚审校检查点",
    "batch_retry": "批量运行已跳过，待重试本章",
    "external_review_pending": "已标记待外审，请平台试发后回改",
}


def _load_quality_summary(chapter_dir: Path) -> Dict[str, Any]:
    quality_path = chapter_dir / "reports" / "quality.json"
    if not quality_path.is_file():
        return {}
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        guard = quality.get("guard_summary") or {}
        return {
            "mode": quality.get("mode"),
            "overall_pass": quality.get("overall_pass"),
            "overall_status": guard.get("overall_status"),
            "blocked_by": guard.get("blocked_by") or [],
        }
    except (json.JSONDecodeError, OSError):
        return {}


def _checkpoint_gate_rows(
    root_dir: Path,
    *,
    limit: int = 0,
    include_quality: bool = False,
) -> List[Dict[str, Any]]:
    chapters_root = root_dir / "workspace" / "chapters"
    if not chapters_root.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
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
        if last_stage not in _CHECKPOINT_ALERT_STAGES:
            continue
        chapter_id = str(
            checkpoint.get("chapter_id") or chapter_dir.name.replace("chapter_", "")
        )
        row: Dict[str, Any] = {
            "chapter_id": chapter_id,
            "last_stage": last_stage,
            "message": _PIPELINE_ALERT_MESSAGES.get(last_stage, last_stage)
            if include_quality
            else last_stage,
            "completed_stages": checkpoint.get("completed_stages") or [],
            "timestamp": checkpoint.get("timestamp"),
            "quality": _load_quality_summary(chapter_dir) if include_quality else {},
            "source": "checkpoint",
        }
        rows.append(row)
        if limit and len(rows) >= limit:
            break
    return rows


def _scan_checkpoint_alerts(root_dir: Path, *, limit: int = 20) -> List[Dict[str, Any]]:
    return _checkpoint_gate_rows(root_dir, limit=limit, include_quality=False)


def _append_retry_and_external_alerts(
    root_dir: Path,
    alerts: List[Dict[str, Any]],
) -> None:
    seen_ids = {a["chapter_id"] for a in alerts}
    for item in list_pending_retries(root_dir):
        cid = str(item.get("chapter_id") or "")
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        alerts.append(
            {
                "chapter_id": cid,
                "last_stage": "batch_retry",
                "message": item.get("message") or _PIPELINE_ALERT_MESSAGES["batch_retry"],
                "completed_stages": [],
                "timestamp": item.get("timestamp"),
                "quality": {},
                "source": "batch_retry",
                "arc_id": item.get("arc_id"),
                "retry_reason": item.get("reason"),
            }
        )
    try:
        from novel_agent.services.external_review import list_pending_external

        for item in list_pending_external(root_dir):
            cid = str(item.get("chapter_id") or "")
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)
            alerts.append(
                {
                    "chapter_id": cid,
                    "last_stage": "external_review_pending",
                    "message": _PIPELINE_ALERT_MESSAGES["external_review_pending"],
                    "completed_stages": [],
                    "timestamp": item.get("updated_at"),
                    "quality": {},
                    "source": "external_review",
                    "external_note": item.get("note", ""),
                }
            )
    except Exception:
        pass


def _sort_alerts(alerts: List[Dict[str, Any]]) -> None:
    alerts.sort(
        key=lambda a: (
            a.get("last_stage") not in ("quality_blocked", "batch_retry"),
            str(a.get("chapter_id")),
        )
    )


def collect_pipeline_alerts(root_dir: Path) -> List[Dict[str, Any]]:
    """Same chapter set as GET /api/pipeline-alerts (for UI badges / ops)."""
    alerts = _checkpoint_gate_rows(root_dir, include_quality=True)
    _append_retry_and_external_alerts(root_dir, alerts)
    _sort_alerts(alerts)
    return alerts


def pipeline_alerts_cache_signature(root_dir: Path) -> Dict[str, Any]:
    """Lightweight fingerprint for cache invalidation (stat only, no JSON reads)."""
    sig: Dict[str, Any] = {
        "retry_mtime": 0.0,
        "external_mtime": 0.0,
        "ckpt_max": 0.0,
        "ckpt_n": 0,
    }
    retry = root_dir / "workspace" / "reports" / "batch_retry_queue.json"
    if retry.is_file():
        try:
            sig["retry_mtime"] = retry.stat().st_mtime
        except OSError:
            pass
    external = root_dir / "workspace" / "reports" / "external_review.json"
    if external.is_file():
        try:
            sig["external_mtime"] = external.stat().st_mtime
        except OSError:
            pass
    chapters = root_dir / "workspace" / "chapters"
    if chapters.is_dir():
        for checkpoint in chapters.glob("chapter_*/checkpoint.json"):
            try:
                sig["ckpt_n"] += 1
                sig["ckpt_max"] = max(sig["ckpt_max"], checkpoint.stat().st_mtime)
            except OSError:
                pass
    return sig


def invalidate_pipeline_alerts_cache(root_dir: Path) -> None:
    path = root_dir / _ALERT_COUNT_CACHE_REL
    try:
        if path.is_file():
            path.unlink()
    except OSError as exc:
        logger.debug("Failed to invalidate pipeline alert cache: %s", exc)


def count_pipeline_alerts_cached(root_dir: Path) -> int:
    """Cached variant for book-library list (mtime-invalidated)."""
    cache_path = root_dir / _ALERT_COUNT_CACHE_REL
    sig = pipeline_alerts_cache_signature(root_dir)
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("signature") == sig and isinstance(cached.get("count"), int):
                return int(cached["count"])
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    count = count_pipeline_alerts(root_dir)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"signature": sig, "count": count}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.debug("Failed to write pipeline alert cache: %s", exc)
    return count


def count_pipeline_alerts(root_dir: Path) -> int:
    """Fast count aligned with collect_pipeline_alerts (skips quality.json reads)."""
    seen: Set[str] = {row["chapter_id"] for row in _checkpoint_gate_rows(root_dir)}
    count = len(seen)
    for item in list_pending_retries(root_dir):
        cid = str(item.get("chapter_id") or "")
        if cid and cid not in seen:
            seen.add(cid)
            count += 1
    try:
        from novel_agent.services.external_review import list_pending_external

        for item in list_pending_external(root_dir):
            cid = str(item.get("chapter_id") or "")
            if cid and cid not in seen:
                seen.add(cid)
                count += 1
    except Exception:
        pass
    return count


def summarize_pipeline_pending(root_dir: Path) -> Dict[str, Any]:
    alerts = collect_pipeline_alerts(root_dir)
    retries = [a for a in alerts if a.get("last_stage") == "batch_retry"]
    gate_blocked = [a for a in alerts if a.get("last_stage") in _CHECKPOINT_ALERT_STAGES]
    external = [a for a in alerts if a.get("last_stage") == "external_review_pending"]
    retry_items = list_pending_retries(root_dir)
    return {
        "pending_retry_count": len(retries),
        "pending_gate_count": len(gate_blocked),
        "pending_external_count": len(external),
        "pending_total": len(alerts),
        "retries": retry_items[:10],
        "gate_blocked": gate_blocked[:10],
    }