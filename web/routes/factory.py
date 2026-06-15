"""Product-level AI factory dashboard API routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import logging

import web.context as ws_server
from web.deps import ProjectSession, RequireProjectDep, get_project_session
from web.factory_summaries import (
    build_factory_dashboard,
    summarize_project_book,
)

router = APIRouter()
logger = logging.getLogger("web.routes.factory")


FactoryMode = Literal[
    "newbie_auto",
    "author_copilot",
    "platform_review",
    "longform_stable",
    "studio",
]


class FactoryModeRequest(BaseModel):
    mode: FactoryMode


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _load_project_meta(root: Path) -> Dict[str, Any]:
    return _read_json(root / "config" / "project_meta.json")


def _write_project_meta(root: Path, meta: Dict[str, Any]) -> None:
    meta_path = root / "config" / "project_meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _running_task_count() -> int:
    try:
        tasks = ws_server._get_task_manager().list_tasks()
    except Exception:
        return 0
    return len([task for task in tasks if task.get("status") in ("pending", "running")])


@router.get("/api/factory/dashboard")
def get_factory_dashboard(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    return build_factory_dashboard(session.root_dir, session.project_id, _running_task_count())


@router.get("/api/factory/studio")
def get_factory_studio(session: ProjectSession = Depends(get_project_session)) -> Dict[str, Any]:
    registry = ws_server.project_manager._read_registry()
    active_id = session.project_id
    active_running = _running_task_count()
    books: List[Dict[str, Any]] = []
    for pid, info in registry.get("projects", {}).items():
        project_dir = ws_server.BASE_DIR / "projects" / pid
        if not project_dir.is_dir():
            continue
        try:
            from novel_agent.services.pipeline_pending import count_pipeline_alerts_cached

            pending_alert_count = count_pipeline_alerts_cached(project_dir)
        except Exception:
            pending_alert_count = 0
        enriched = dict(info)
        enriched["pending_alert_count"] = pending_alert_count
        running_tasks = active_running if pid == active_id else 0
        books.append(
            summarize_project_book(
                pid,
                project_dir,
                enriched,
                running_tasks=running_tasks,
            )
        )

    columns = [
        {"id": "empty", "label": "未开书"},
        {"id": "planning", "label": "筹备中"},
        {"id": "ready", "label": "可生产"},
        {"id": "running", "label": "生产中"},
        {"id": "blocked", "label": "待修复"},
        {"id": "complete", "label": "已完成"},
    ]
    by_column: Dict[str, List[Dict[str, Any]]] = {col["id"]: [] for col in columns}
    for book in books:
        column_id = str(book.get("kanban_column") or "empty")
        if column_id not in by_column:
            column_id = "empty"
        by_column[column_id].append(book)

    summary = {
        "total": len(books),
        "running": len(by_column["running"]),
        "blocked": len(by_column["blocked"]),
        "ready": len(by_column["ready"]),
        "complete": len(by_column["complete"]),
    }
    return {
        "summary": summary,
        "columns": columns,
        "books_by_column": by_column,
        "books": books,
        "active_project_id": active_id,
    }


@router.put("/api/factory/mode")
def update_factory_mode(
    req: FactoryModeRequest,
    session: ProjectSession = Depends(get_project_session),
) -> Dict[str, str]:
    root = session.root_dir
    meta = _load_project_meta(root)
    meta["factory_mode"] = req.mode
    _write_project_meta(root, meta)
    return {"status": "updated", "mode": req.mode}