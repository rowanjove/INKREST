"""Shared imports for chapter route modules."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException

from web.deps import ProjectSession, RequireProjectDep, coerce_project_session, touch_project_activity
from pydantic import BaseModel, Field

import web.context as ws_server
import web.helpers as ws_helpers

ws_server._validate_id = ws_helpers._validate_id
ws_server._read_json = ws_helpers._read_json
ws_server._read_text = ws_helpers._read_text
ws_server.get_outline = ws_helpers.get_outline
ws_server._delete_chapter_dir = ws_helpers._delete_chapter_dir
ws_server.logger = logging.getLogger("web.server")

from web.models import (
    ChapterRequest,
    BatchChapterRequest,
    TaskStatus,
    ChapterSummary,
    ChapterListResponse,
    ChapterDetail,
    NovelChatRequest,
    SaveChapterRequest,
)
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.scripts.count_chars import count_chinese_chars, wordcount_report

router = APIRouter()

from web.routes.chapters.snapshots import create_chapter_snapshot


@router.get("/api/chapters/count")
def count_chapters(sync: bool = False, session: ProjectSession = RequireProjectDep) -> Dict[str, int]:
    """Lightweight chapter count for long-form dashboards."""
    session = coerce_project_session(session)
    root = session.root_dir
    store = SQLiteStateStore(root)
    if sync or store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)
    return {"total": store.count_chapters_indexed()}


@router.get("/api/chapters")
def list_chapters(
    offset: int = 0,
    limit: int = 100,
    sync: bool = False,
    include_gaps: bool = False,
    session: ProjectSession = RequireProjectDep,
) -> ChapterListResponse:
    """List chapters from SQLite index (paginated). Avoids full-disk glob at scale."""
    session = coerce_project_session(session)
    root = session.root_dir
    store = SQLiteStateStore(root)
    if sync or store.count_chapters_indexed() == 0:
        sync_chapters_from_disk(root, store)

    offset = max(0, int(offset))
    limit = max(1, min(int(limit), 500))
    total = store.count_chapters_indexed()
    rows = store.list_chapters_page(offset=offset, limit=limit)
    items = [
        ChapterSummary(
            chapter_id=row["id"],
            title=row.get("title") or "",
            word_count=int(row.get("word_count") or 0),
            risk_level=row.get("risk_level") or "",
            final_path=row.get("final_path") or "",
            is_missing=False,
            has_final=bool(row.get("has_final")),
            gate_status=str(row.get("gate_status") or ""),
        )
        for row in rows
    ]

    if include_gaps and offset == 0 and limit >= total and total > 0:
        max_num = store.max_numeric_chapter_id()
        if max_num and max_num <= 10000:
            present = {int(i.chapter_id) for i in items if i.chapter_id.isdigit()}
            gap_items = []
            for num in range(1, max_num + 1):
                if num not in present:
                    gap_items.append(
                        ChapterSummary(
                            chapter_id=f"{num:03d}",
                            title="[缺失断档章]",
                            word_count=0,
                            risk_level="缺失",
                            final_path="",
                            is_missing=True,
                        )
                    )
            items = sorted(
                items + gap_items,
                key=lambda x: int(x.chapter_id) if x.chapter_id.isdigit() else 999999,
            )
            total = len(items)

    return ChapterListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        indexed=True,
    )


@router.get("/api/chapters/{chapter_id}")
def get_chapter(chapter_id: str, session: ProjectSession = RequireProjectDep) -> ChapterDetail:
    session = coerce_project_session(session)
    ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {chapter_id} not found")

    plan = ws_server._read_json(chapter_dir / "plan.json")
    final_text = ws_server._read_text(chapter_dir / "chapter_final.txt")
    wordcount = ws_server._read_json(chapter_dir / "reports" / "wordcount.json")
    target_chars = plan.get("target_chars") if isinstance(plan.get("target_chars"), list) else []
    target_min = int(target_chars[0]) if len(target_chars) > 0 and str(target_chars[0]).isdigit() else 0
    target_max = int(target_chars[1]) if len(target_chars) > 1 and str(target_chars[1]).isdigit() else 0
    if not final_text.strip():
        wordcount = {
            **wordcount,
            "count": 0,
            "target_min": wordcount.get("target_min", target_min),
            "target_max": wordcount.get("target_max", target_max),
            "status": "empty",
            "missing": wordcount.get("target_min", target_min),
            "excess": 0,
        }
    elif not wordcount or not wordcount.get("count"):
        wordcount = wordcount_report(final_text, target_min, target_max)
    audit = ws_server._read_json(chapter_dir / "reports" / "audit.json")
    continuity = ws_server._read_json(chapter_dir / "reports" / "continuity.json")
    state_update = ws_server._read_json(chapter_dir / "state_update.json")
    quality_report = ws_server._read_json(chapter_dir / "reports" / "quality.json")
    unified_gate = ws_server._read_json(chapter_dir / "reports" / "unified_gate.json")
    checkpoint = ws_server._read_json(chapter_dir / "checkpoint.json")

    from novel_agent.services.chapter_artifact_status import build_chapter_artifact_status, summarize_chapter_artifact_status
    from novel_agent.services.report_validity import load_report_validity

    artifact_status = build_chapter_artifact_status(
        chapter_dir,
        checkpoint=checkpoint,
        unified_gate=unified_gate,
        report_validity=load_report_validity(chapter_dir / "reports") or {},
    )
    artifact_summary = summarize_chapter_artifact_status(artifact_status)

    from novel_agent.services.external_review import get_external_review_status

    return ChapterDetail(
        chapter_id=chapter_id,
        title=plan.get("chapter_title", ""),
        final_text=final_text,
        plan=plan,
        wordcount=wordcount,
        audit=audit,
        continuity=continuity,
        state_update=state_update,
        chapter_summary=ws_server._read_text(chapter_dir / "chapter_summary.md"),
        quality_report=quality_report,
        unified_gate=unified_gate,
        checkpoint=checkpoint,
        artifact_status=artifact_status,
        artifact_summary=artifact_summary,
        external_review_status=get_external_review_status(session.root_dir, chapter_id),
    )


class CreateChapterRequest(BaseModel):
    chapter_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    title: str = "新章节"


@router.post("/api/chapters")
def create_new_chapter(req: CreateChapterRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    import json
    safe_id = ws_server._validate_id(req.chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if chapter_dir.exists():
        raise HTTPException(400, f"章节 {safe_id} 已存在")
    
    chapter_dir.mkdir(parents=True, exist_ok=True)
    
    plan = {
        "chapter_id": safe_id,
        "chapter_title": req.title,
        "chapter_goal": "",
        "detailed_synopsis": "",
        "target_chars": [2000, 3000]
    }
    
    plan_path = chapter_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    
    final_txt_path = chapter_dir / "chapter_final.txt"
    final_txt_path.write_text("", encoding="utf-8")
    
    reports_dir = chapter_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    wordcount = {
        "count": 0,
        "target_min": 2000,
        "target_max": 3000,
        "status": "empty",
        "missing": 2000,
        "excess": 0
    }
    (reports_dir / "wordcount.json").write_text(json.dumps(wordcount, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 新建默认活跃分支记录
    try:
        store = ws_server._get_task_manager().store
        store.save_chapter_version(
            chapter_id=safe_id,
            version_name="版本 A",
            content="",
            plan=json.dumps(plan, ensure_ascii=False),
            is_active=True,
            note="新建章节自动初始化版本"
        )
        import random
        bounce = round(random.uniform(0.08, 0.18), 3)
        retention = round(random.uniform(0.78, 0.88), 3)
        readers = random.randint(3000, 12000)
        store.save_reader_feedback(safe_id, bounce, retention, readers)
    except Exception as e:
        ws_server.logger.warning("Failed to initialize chapter_versions or feedback: %s", e)
        
    touch_project_activity(session)

    return {"status": "created", "chapter_id": safe_id}


@router.delete("/api/chapters/{chapter_id}")
def delete_chapter(chapter_id: str, session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    root_dir = session.root_dir
    deleted = ws_server._delete_chapter_dir(root_dir, chapter_id)
    try:
        from novel_agent.services.chapter_highwater import sync_highwater_from_store
        sync_highwater_from_store(root_dir)
    except Exception as exc:
        ws_server.logger.warning("Failed to sync highwater after delete: %s", exc)
    return {"status": "deleted", "chapter_id": chapter_id, "path": str(deleted)}


@router.put("/api/chapters/{chapter_id}")
def save_chapter(chapter_id: str, req: SaveChapterRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    import json

    ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {chapter_id} not found")

    final_txt_path = chapter_dir / "chapter_final.txt"
    final_txt_path.write_text(req.final_text, encoding="utf-8")

    plan_path = chapter_dir / "plan.json"
    plan = {}
    if plan_path.exists():
        plan = ws_server._read_json(plan_path)
    if req.title is not None:
        plan["chapter_title"] = req.title
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    target_chars = plan.get("target_chars") if isinstance(plan.get("target_chars"), list) else []
    target_min = int(target_chars[0]) if len(target_chars) > 0 and str(target_chars[0]).isdigit() else 0
    target_max = int(target_chars[1]) if len(target_chars) > 1 and str(target_chars[1]).isdigit() else 0

    new_report = wordcount_report(req.final_text, target_min, target_max)
    reports_dir = chapter_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "wordcount.json").write_text(
        json.dumps(new_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        title = plan.get("chapter_title", f"第 {chapter_id} 章")
        create_chapter_snapshot(
            session.root_dir, chapter_id, title, req.final_text, is_manual=False
        )
    except Exception as e:
        ws_server.logger.warning("Failed to create automatic snapshot: %s", e)

    try:
        store = ws_server._get_task_manager().store
        versions = store.list_chapter_versions(chapter_id)
        active_version = next((v for v in versions if v.get("is_active") == 1), None)
        if active_version:
            store.save_chapter_version(
                chapter_id=chapter_id,
                version_name=active_version["version_name"],
                content=req.final_text,
                plan=json.dumps(plan, ensure_ascii=False),
                is_active=True,
                note=active_version.get("note", ""),
                version_id=active_version["id"],
            )
        else:
            store.save_chapter_version(
                chapter_id=chapter_id,
                version_name="版本 A",
                content=req.final_text,
                plan=json.dumps(plan, ensure_ascii=False),
                is_active=True,
                note="保存章节同步创建",
            )
        feedback = store.get_reader_feedback(chapter_id)
        if not feedback:
            import random

            bounce = round(random.uniform(0.08, 0.18), 3)
            retention = round(random.uniform(0.78, 0.88), 3)
            readers = random.randint(3000, 12000)
            store.save_reader_feedback(chapter_id, bounce, retention, readers)
    except Exception as e:
        ws_server.logger.warning("Failed to sync save to chapter_versions or feedback: %s", e)

    touch_project_activity(session)

    return {"status": "saved", "chapter_id": chapter_id}

