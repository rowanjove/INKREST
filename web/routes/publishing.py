"""Unified publication-center API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from novel_agent.control.platform_profiles import PLATFORM_PROFILES
from novel_agent.control.longform_flags import flag_enabled
from novel_agent.services.publishing_workspace import build_publishing_workspace, publication_formats
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.deps import (
    ProjectSession,
    RequireProjectDep,
    current_project_info,
    task_manager_for,
    touch_project_activity,
)
from web.helpers import _validate_id

router = APIRouter(tags=["publishing"])


class UpdatePlatformRequest(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32)


class SaveReaderFeedbackRequest(BaseModel):
    chapter_id: str = Field(..., min_length=1, max_length=64)
    bounce_rate: float = Field(..., ge=0, le=1)
    retention_rate: float = Field(..., ge=0, le=1)
    active_readers: int = Field(..., ge=0, le=1_000_000_000)


class PublicationExportRequest(BaseModel):
    format: Literal["txt", "markdown", "md", "docx", "epub", "pdf"]
    title: str = Field(default="未命名小说", min_length=1, max_length=200)
    chapter_ids: list[str] = Field(default_factory=list, max_length=500)
    acknowledge_warnings: bool = False


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def _safe_filename(title: str, extension: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", title).strip(" .")
    cleaned = cleaned[:120] or "未命名小说"
    return f"{cleaned}{extension}"


def _publishing_workspace_payload(
    session: ProjectSession,
    *,
    chapter_id: str = "",
    query: str = "",
    offset: int = 0,
    limit: int = 100,
) -> dict:
    if chapter_id:
        _validate_id(chapter_id, "chapter_id")
    return build_publishing_workspace(
        session.root_dir,
        project_id=session.project_id or session.root_dir.name,
        project_info=current_project_info(session),
        selected_chapter_id=chapter_id,
        query=query,
        offset=offset,
        limit=limit,
    ).model_dump(mode="json")


@router.get("/api/publishing/workspace")
def get_publishing_workspace(
    session: ProjectSession = RequireProjectDep,
    chapter_id: str = Query(default="", max_length=64),
    query: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> dict:
    return _publishing_workspace_payload(
        session,
        chapter_id=chapter_id,
        query=query,
        offset=offset,
        limit=limit,
    )


@router.put("/api/publishing/platform")
def put_publishing_platform(
    body: UpdatePlatformRequest,
    session: ProjectSession = RequireProjectDep,
) -> dict:
    platform = body.platform.strip().lower()
    if platform not in PLATFORM_PROFILES:
        raise HTTPException(422, "不支持的发布平台")
    meta_path = session.root_dir / "config" / "project_meta.json"
    meta: dict = {}
    if meta_path.is_file():
        try:
            value = json.loads(meta_path.read_text(encoding="utf-8"))
            meta = value if isinstance(value, dict) else {}
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise HTTPException(409, "项目元数据已损坏，请先修复后再保存平台")
    meta["platform"] = platform
    _atomic_json(meta_path, meta)
    touch_project_activity(session)
    return _publishing_workspace_payload(session)


@router.put("/api/publishing/feedback")
def put_publishing_feedback(
    body: SaveReaderFeedbackRequest,
    session: ProjectSession = RequireProjectDep,
) -> dict:
    chapter_id = _validate_id(body.chapter_id, "chapter_id")
    store = SQLiteStateStore(session.root_dir)
    if store.get_manuscript_document(chapter_id) is None:
        raise HTTPException(404, "正文章节不存在")
    store.save_reader_feedback(
        chapter_id,
        body.bounce_rate,
        body.retention_rate,
        body.active_readers,
    )
    touch_project_activity(session)
    return _publishing_workspace_payload(session, chapter_id=chapter_id)


@router.post("/api/publishing/export")
async def post_publishing_export(
    body: PublicationExportRequest,
    session: ProjectSession = RequireProjectDep,
) -> dict:
    workspace = build_publishing_workspace(
        session.root_dir,
        project_id=session.project_id or session.root_dir.name,
        project_info=current_project_info(session),
    )
    if not workspace.preflight.can_export:
        raise HTTPException(
            409,
            {
                "code": "EXPORT_PREFLIGHT_BLOCKED",
                "message": "发布预检仍有阻断项",
                "preflight": workspace.preflight.model_dump(mode="json"),
            },
        )
    if workspace.preflight.warning_count and not body.acknowledge_warnings:
        raise HTTPException(
            409,
            {
                "code": "EXPORT_WARNINGS_NOT_ACKNOWLEDGED",
                "message": "请确认发布警告后再导出",
                "preflight": workspace.preflight.model_dump(mode="json"),
            },
        )
    export_format = "markdown" if body.format == "md" else body.format
    format_row = next(item for item in workspace.formats if item["id"] == export_format)
    if not format_row["available"]:
        raise HTTPException(503, f"{format_row['label']} 导出组件尚未安装")

    streaming_enabled = flag_enabled("m1_streaming_export", session.root_dir)
    task_id = await task_manager_for(session).submit_export(
        export_format=export_format,
        title=body.title,
        chapter_ids=body.chapter_ids or None,
        extension=str(format_row["extension"]),
        streaming=streaming_enabled,
    )
    touch_project_activity(session)
    return {
        "task_id": task_id,
        "status": "pending",
        "format": export_format,
        "mode": "streaming_background" if streaming_enabled else "background_compatibility",
        "filename": _safe_filename(body.title, str(format_row["extension"])),
    }


@router.get("/api/publishing/export/{task_id}")
async def get_publishing_export_task(
    task_id: str,
    session: ProjectSession = RequireProjectDep,
) -> dict:
    task = await task_manager_for(session).get_task_async(task_id)
    if not task or task.get("task_type") != "export":
        raise HTTPException(404, "导出任务不存在")
    return task


@router.post("/api/publishing/export/{task_id}/cancel")
async def cancel_publishing_export(
    task_id: str,
    session: ProjectSession = RequireProjectDep,
) -> dict:
    manager = task_manager_for(session)
    task = await manager.get_task_async(task_id)
    if not task or task.get("task_type") != "export":
        raise HTTPException(404, "导出任务不存在")
    success = await manager.abort_task(task_id)
    return {"task_id": task_id, "status": "cancelled" if success else task["status"]}


@router.get("/api/publishing/export/{task_id}/download")
async def download_publishing_export(
    task_id: str,
    session: ProjectSession = RequireProjectDep,
) -> FileResponse:
    task = await task_manager_for(session).get_task_async(task_id)
    if not task or task.get("task_type") != "export":
        raise HTTPException(404, "导出任务不存在")
    if task.get("status") != "succeeded":
        raise HTTPException(409, "导出任务尚未完成")
    result = task.get("result") or {}
    output = Path(str(result.get("path") or ""))
    project_root = Path(session.root_dir).resolve()
    try:
        output.resolve().relative_to((project_root / "workspace" / "exports").resolve())
    except ValueError as exc:
        raise HTTPException(500, "导出文件路径无效") from exc
    if not output.is_file():
        raise HTTPException(410, "导出文件已清理，请重新导出")
    filename = _safe_filename(
        str(result.get("title") or "未命名小说"),
        str(next(
            item["extension"] for item in publication_formats() if item["id"] == result.get("format")
        )),
    )
    return FileResponse(
        output,
        filename=filename,
        media_type="application/octet-stream",
        background=BackgroundTask(output.unlink, missing_ok=True),
    )
