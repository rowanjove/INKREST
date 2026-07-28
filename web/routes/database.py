import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel, Field

from web.security import ACCESS_TOKEN_ENV, ACCESS_TOKEN_HEADER
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session, task_manager_for
from novel_agent.control.calibration import build_calibration_report

ws_server.get_outline = ws_helpers.get_outline
ws_server.list_chapters = ws_helpers.list_chapters
ws_server.build_calibration_report = build_calibration_report
from web.models import (
    StateView,
    TimelineView,
)
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.control.narrative_debt import classify_debt
from novel_agent.control.scale_profile import build_upgrade_pressure, resolve_scale_profile
from novel_agent.dashboard import build_dashboard_html
from novel_agent.exporters.docx_exporter import export_docx
from novel_agent.exporters.markdown_exporter import export_markdown

router = APIRouter()


# ---- Database ----


class ClearDatabaseRequest(BaseModel):
    confirm: bool = Field(
        False,
        description="Must be true to clear narrative state.",
    )
    include_operational: bool = Field(
        False,
        description="Also clear tasks, cost logs, and prompt/asset version history.",
    )


@router.post("/api/database/clear")
def clear_database(
    body: ClearDatabaseRequest = Body(default_factory=ClearDatabaseRequest),
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    if not body.confirm:
        raise HTTPException(
            400,
            "Destructive operation: set confirm=true in request body.",
        )
    store = SQLiteStateStore(session.root_dir)
    cleared = store.clear_narrative_state(include_operational=body.include_operational)
    return {
        "status": "cleared",
        "tables_cleared": cleared,
        "include_operational": body.include_operational,
        "access_token_required": bool(os.environ.get(ACCESS_TOKEN_ENV, "")),
        "access_token_header": ACCESS_TOKEN_HEADER,
    }


@router.post("/api/database/export-yaml-mirror")
def export_yaml_mirror_snapshot(
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Export SQLite narrative state to state/*.yaml without enabling live dual-write."""
    session = coerce_project_session(session)
    from novel_agent.state.yaml_mirror import export_yaml_mirror, resolve_yaml_mirror_mode

    counts = export_yaml_mirror(session.root_dir)
    return {
        "status": "exported",
        "mode": resolve_yaml_mirror_mode(session.root_dir),
        "counts": counts,
    }


def export_markdown_internal(root_dir: Path, output_path: Path, chapter_ids: Optional[List[str]] = None, title: str = "未命名小说"):
    export_markdown(root_dir, output_path, chapter_ids=chapter_ids, title=title)


def export_docx_internal(root_dir: Path, output_path: Path, chapter_ids: Optional[List[str]] = None, title: str = "未命名小说"):
    export_docx(root_dir, output_path, chapter_ids=chapter_ids, title=title)


# ---- Export ----

@router.post("/api/export")
def export_novel(
    format: str = Query(..., pattern="^(txt|epub|pdf|markdown|docx|md)$"),
    chapter_ids: Optional[str] = Query(None, description="Comma-separated chapter IDs, or empty for all"),
    title: str = Query("未命名小说", description="Book title"),
    project_id: Optional[str] = Query(None, description="Project ID"),
    session: ProjectSession = RequireProjectDep,
) -> FileResponse:
    session = coerce_project_session(session)
    """Export chapters in the specified format."""
    from novel_agent.exporters import export_txt, export_epub, export_pdf

    if project_id:
        ws_server._validate_id(project_id, "project_id")
        root_dir = ws_server.BASE_DIR / "projects" / project_id
        if not root_dir.exists():
            raise HTTPException(404, f"Project {project_id} not found")
    else:
        root_dir = session.root_dir

    ids = [c.strip() for c in chapter_ids.split(",")] if chapter_ids else None
    
    # 规范化文件后缀
    ext = format
    if format == "markdown":
        ext = "md"
    suffix = f".{ext}"
    
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix="novel_export_")
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        if format == "txt":
            export_txt(root_dir, tmp_path, chapter_ids=ids, include_title=True)
        elif format == "epub":
            export_epub(root_dir, tmp_path, chapter_ids=ids, title=title)
        elif format == "pdf":
            export_pdf(root_dir, tmp_path, chapter_ids=ids, title=title)
        elif format in ("markdown", "md"):
            export_markdown_internal(root_dir, tmp_path, chapter_ids=ids, title=title)
        elif format == "docx":
            export_docx_internal(root_dir, tmp_path, chapter_ids=ids, title=title)
    except ImportError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Export failed: {exc}")

    filename = f"{title}{suffix}"
    return FileResponse(
        str(tmp_path),
        filename=filename,
        media_type="application/octet-stream",
        background=BackgroundTask(tmp_path.unlink, missing_ok=True),
    )


# ---- State & Narrative Debt ----

@router.get("/api/state")
def get_state(sync: bool = False, session: ProjectSession = RequireProjectDep) -> StateView:
    session = coerce_project_session(session)
    root = session.root_dir
    store = SQLiteStateStore(root)
    if sync:
        try:
            from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
            sync_chapters_from_disk(root, store)
        except Exception as exc:
            import logging
            logging.getLogger("web.server").error("Failed to sync chapters during state query: %s", exc)

    chapters = store.get_chapters()
    current = chapters[-1]["id"] if chapters else "000"
    
    foreshadows = classify_debt(store.list_foreshadows(), current, default_period=10, weight=1.0)
    hooks = classify_debt(store.list_hooks(), current, default_period=10, weight=1.0)
    
    return StateView(
        characters=store.list_characters(),
        foreshadows=foreshadows,
        hooks=hooks,
        objects=store.list_objects(),
        events=store.list_events(),
        threads=store.list_threads(),
    )


@router.get("/api/state/timeline")
def get_timeline(session: ProjectSession = RequireProjectDep) -> TimelineView:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    items = store.search_timeline("", limit=500)

    nodes = [i for i in items if i.get("kind") == "node"]
    edges = [i for i in items if i.get("kind") == "edge"]
    foreshadows = [i for i in items if i.get("kind") == "foreshadow"]
    hooks = [i for i in items if i.get("kind") == "hook"]

    return TimelineView(
        nodes=nodes,
        edges=edges,
        foreshadows=foreshadows,
        hooks=hooks,
    )


@router.get("/api/events")
def search_events(
    query: str = "",
    limit: int = 20,
    session: ProjectSession = RequireProjectDep,
) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    return store.search_events(query, limit)


from pydantic import BaseModel

class CollectDebtRequest(BaseModel):
    debt_type: str
    debt_id: str
    priority: int = 3


@router.get("/api/control/narrative-debt")
def get_narrative_debt(
    current_chapter: str = "",
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    chapter = current_chapter or "000"
    return {
        "foreshadows": classify_debt(store.list_foreshadows(), chapter, default_period=10, weight=1.0),
        "reader_promises": classify_debt(store.list_reader_promises(), chapter, default_period=8, weight=1.2),
        "secrets": classify_debt(store.list_secrets(), chapter, default_period=12, weight=0.8),
    }


@router.post("/api/control/narrative-debt/collect")
def collect_debt(
    req: CollectDebtRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    table_map = {
        "foreshadows": "foreshadows",
        "foreshadow": "foreshadows",
        "reader_promises": "reader_promises",
        "reader_promise": "reader_promises",
        "secrets": "secrets",
        "secret": "secrets",
        "hooks": "hooks",
        "hook": "hooks"
    }
    table = table_map.get(req.debt_type.lower())
    if not table:
        raise HTTPException(400, f"Unsupported debt type: {req.debt_type}")
    
    store.set_debt_priority(table, req.debt_id, req.priority)
    return {"status": "success", "message": f"Debt {req.debt_id} priority set to {req.priority}"}


@router.get("/api/control/calibration")
def get_calibration_report(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    outline = ws_server.get_outline(session.root_dir)
    root = session.root_dir
    store = SQLiteStateStore(root)
    if store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)
    rows = store.list_chapters_page(offset=0, limit=500)
    chapters = [
        {
            "chapter_id": row.get("id"),
            "title": row.get("title") or "",
            "word_count": int(row.get("word_count") or 0),
        }
        for row in rows
    ]
    current = chapters[-1]["chapter_id"] if chapters else "000"
    debt = get_narrative_debt(current_chapter=current, session=session)
    return ws_server.build_calibration_report(outline, chapters, debt)


@router.get("/api/control/scale-profile")
def get_scale_profile(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    outline = ws_server.get_outline(session.root_dir)
    root = session.root_dir
    store = SQLiteStateStore(root)
    if store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)
    chapter_count = store.count_chapters_indexed()
    profile = outline.get("scale_profile") or resolve_scale_profile(
        target_chapters=outline.get("target_chapters") or chapter_count or 20
    )
    return {
        "profile": profile,
        "current_chapter_count": chapter_count,
        "upgrade_pressure": build_upgrade_pressure(profile, chapter_count),
    }


@router.get("/api/runtime-logs")
async def get_runtime_logs(
    since_id: int = 0,
    limit: int = 200,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    """Agent 流水线实时日志（内存环形缓冲），供生产中心轮询同步。"""
    from web.runtime_log_buffer import list_runtime_logs

    logs = list_runtime_logs(
        since_id=since_id,
        limit=min(max(limit, 1), 500),
        project_id=session.project_id,
    )
    last_id = logs[-1]["id"] if logs else since_id
    return {"logs": logs, "last_id": last_id}


@router.delete("/api/runtime-logs")
async def clear_runtime_logs_api(
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, str]:
    from web.runtime_log_buffer import clear_runtime_logs

    clear_runtime_logs(project_id=session.project_id)
    return {"status": "ok"}


@router.get("/api/llm-logs")
async def get_llm_logs(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    tasks = await task_manager_for(session).list_tasks_async()
    all_logs = []
    for task in tasks:
        logs = task.get("llm_logs", [])
        if logs:
            for entry in logs:
                entry["chapter_id"] = task.get("chapter_id", "")
            all_logs.extend(logs)
    all_logs.sort(key=lambda x: x.get("timestamp", 0))
    total_tokens = sum(entry.get("total_tokens", 0) for entry in all_logs)
    total_latency = sum(entry.get("latency_ms", 0) for entry in all_logs)
    return {
        "logs": all_logs,
        "summary": {
            "call_count": len(all_logs),
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency,
            "avg_latency_ms": int(total_latency / len(all_logs)) if all_logs else 0,
        },
    }


@router.get("/api/dashboard")
def get_dashboard(session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    html = build_dashboard_html(session.root_dir)
    return {"html": html}


class SaveRelationRequest(BaseModel):
    source_char: str
    target_char: str
    relation_type: str
    intensity: float
    since_chapter: int = 1
    last_updated: int = 1
    description: str = ""


@router.get("/api/control/character-relations")
def get_character_relations(session: ProjectSession = RequireProjectDep) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    return store.list_character_relations()


@router.post("/api/control/character-relations")
def save_character_relation(
    req: SaveRelationRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    store.save_character_relation(
        source_char=req.source_char,
        target_char=req.target_char,
        relation_type=req.relation_type,
        intensity=req.intensity,
        since_chapter=req.since_chapter,
        last_updated=req.last_updated,
        description=req.description
    )
    return {"status": "success"}


@router.delete("/api/control/character-relations/{relation_id}")
def delete_character_relation(
    relation_id: int,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    store = SQLiteStateStore(session.root_dir)
    store.delete_character_relation(relation_id)
    return {"status": "success"}
