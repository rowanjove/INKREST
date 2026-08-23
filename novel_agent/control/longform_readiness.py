"""Read-only capability and degradation summary for long-form projects."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .longform_flags import longform_flags
from .runtime_policy import resolve_runtime_policy


def _file_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _task_progress(root: Path) -> dict[str, Any]:
    """Read bounded persisted task progress without creating a database."""

    db_path = root / "data" / "novel.sqlite"
    if not db_path.is_file():
        return {"status": "unavailable:not_initialized", "active": 0, "items": []}
    try:
        from novel_agent.state.sqlite_schema import safe_connection

        with safe_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "select id, task_type, status, checkpoint, created_at, started_at, finished_at "
                "from tasks order by created_at desc limit 100"
            ).fetchall()
        active_statuses = {"pending", "claimed", "running", "retryable"}
        items = []
        active = 0
        for row in rows:
            item = dict(row)
            if str(item.get("status") or "") in active_statuses:
                active += 1
            items.append(
                {
                    "id": str(item.get("id") or ""),
                    "task_type": str(item.get("task_type") or ""),
                    "status": str(item.get("status") or ""),
                    "checkpoint": item.get("checkpoint"),
                }
            )
        return {"status": "ready", "active": active, "items": items[:20]}
    except Exception as exc:
        return {"status": "error", "active": 0, "items": [], "reason": str(exc)}


def _arc_contract_projection(root: Path) -> dict[str, Any]:
    """Read the current arc-contract projections without creating state.

    Arc contracts are stored one-per-arc under ``workspace/arc_contracts``.
    Keep the legacy singular path as a read-only compatibility fallback for
    projects created before the versioned store was introduced.
    """

    contracts_dir = root / "workspace" / "arc_contracts"
    candidates: list[dict[str, Any]] = []
    if contracts_dir.is_dir():
        for path in sorted(contracts_dir.glob("*.json")):
            value = _file_json(path)
            if value and value.get("arc_id"):
                value["_path"] = str(path)
                candidates.append(value)
    if not candidates:
        legacy = _file_json(root / "workspace" / "arc_contract.json")
        if legacy:
            candidates.append(legacy)
    if not candidates:
        return {"status": "missing", "version": None, "arc_count": 0}
    current = max(candidates, key=lambda item: (int(item.get("version") or 0), str(item.get("arc_id") or "")))
    return {
        "status": str(current.get("status") or "unknown"),
        "version": current.get("version"),
        "arc_id": current.get("arc_id"),
        "arc_count": len(candidates),
    }


def build_longform_readiness(root_dir: Path) -> dict[str, Any]:
    root = Path(root_dir)
    policy = resolve_runtime_policy(root)
    try:
        from novel_agent.pipeline import load_pipeline_settings

        runtime_settings = load_pipeline_settings(root).get("runtime", {}) or {}
    except Exception:
        runtime_settings = {}
    flags = longform_flags(root)
    fts: dict[str, Any]
    db_path = root / "data" / "novel.sqlite"
    if not db_path.is_file():
        fts = {"available": False, "status": "unavailable:not_initialized", "index": "story_search_fts"}
    else:
        try:
            from novel_agent.state.sqlite_schema import safe_connection

            with safe_connection(db_path) as conn:
                row = conn.execute("select value from app_metadata where key = 'fts5_status'").fetchone()
            raw = str(row[0] if row else "unavailable:not_initialized")
            fts = {"available": raw == "available", "status": raw, "index": "story_search_fts"}
        except Exception as exc:
            fts = {"status": "error", "error": str(exc)}
    try:
        from novel_agent.state.vector_store import CHROMA_AVAILABLE
    except Exception:
        CHROMA_AVAILABLE = False
    embedding = _file_json(root / "workspace" / "reports" / "embedding_readiness.json")
    retrieval_latest = _file_json(root / "workspace" / "reports" / "retrieval_latest.json")
    vector_status = "ready" if CHROMA_AVAILABLE else "sqlite_fallback"
    if embedding.get("status"):
        vector_status = str(embedding["status"])
    impact_path = root / "workspace" / "outline_impact.json"
    arc = _arc_contract_projection(root)
    impact = _file_json(impact_path)
    degraded: list[str] = []
    if fts.get("status") not in {"ready", "available"}:
        degraded.append("fts")
    if vector_status not in {"ready", "available"}:
        degraded.append("embedding")
    try:
        from novel_agent.retrieval.reranker import resolve_reranker_readiness

        reranker = resolve_reranker_readiness(root)
    except Exception as exc:
        reranker = {"status": "error", "mode": "deterministic", "reason": str(exc)}
    if reranker.get("status") == "invalid":
        degraded.append("reranker_config")
    tasks = _task_progress(root)
    if not flags.get("m2_hybrid_retrieval", False):
        degraded.append("hybrid_retrieval_disabled")
    return {
        "scale": str(policy.scale or "medium"),
        "target_chapters": int(policy.target_chapters or 0),
        "budget": {"max_workers": int(runtime_settings.get("max_workers") or 4), "pipeline_tier": policy.pipeline_tier},
        "flags": flags,
        "retrieval": {
            "fts": fts,
            "embedding": {"status": vector_status, "chroma_available": bool(CHROMA_AVAILABLE)},
            "chroma": {"status": "ready" if CHROMA_AVAILABLE else "unavailable"},
            "reranker": reranker,
            "required_fact_coverage": {
                "status": "ready" if retrieval_latest.get("coverage") is not None else "unknown",
                "value": retrieval_latest.get("coverage"),
                "reason": "latest Context Pack" if retrieval_latest.get("coverage") is not None else "no persisted acceptance window",
            },
            "latest": retrieval_latest,
            "degraded": degraded,
        },
        "arc_contract": arc,
        "outline_impact": impact,
        "tasks": tasks,
        "badges": {
            "design_supported": True,
            "stress_verified": (root / "logs" / "longform-stress-verified.json").is_file(),
            "real_run_verified": (root / "docs" / "reports" / "longform" / "real-run-verified.json").is_file(),
        },
    }


__all__ = ["build_longform_readiness"]
