"""Shared imports for chapter route modules."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException
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
    ChapterDetail,
    NovelChatRequest,
    SaveChapterRequest,
)
from novel_agent.scripts.count_chars import count_chinese_chars, wordcount_report
from novel_agent.services.manuscript_workspace import apply_plain_text_to_manuscript
from novel_agent.state.manuscript_repository import DocumentConflictError
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session

router = APIRouter()


def create_chapter_snapshot(root_dir: Path, chapter_id: str, title: str, final_text: str, is_manual: bool = False) -> Dict[str, Any]:
    import json
    import time
    from datetime import datetime
    
    chapter_dir = root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    snapshots_dir = chapter_dir / ".snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time() * 1000)
    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    from novel_agent.scripts.count_chars import count_chinese_chars
    word_count = count_chinese_chars(final_text)
    
    snapshot_data = {
        "timestamp": timestamp,
        "datetime": dt_str,
        "title": title,
        "final_text": final_text,
        "word_count": word_count,
        "is_manual": is_manual
    }
    
    snapshot_file = snapshots_dir / f"snapshot_{timestamp}.json"
    snapshot_file.write_text(json.dumps(snapshot_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    snapshot_files = sorted(snapshots_dir.glob("snapshot_*.json"), key=lambda f: f.stat().st_mtime)
    if len(snapshot_files) > 30:
        for old_file in snapshot_files[:-30]:
            try:
                old_file.unlink()
            except OSError:
                pass
                
    return snapshot_data


@router.get("/api/chapters/{chapter_id}/snapshots")
def get_chapter_snapshots(
    chapter_id: str,
    session: ProjectSession = RequireProjectDep,
) -> List[Dict[str, Any]]:
    import json
    session = coerce_project_session(session)
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")
        
    snapshots_dir = chapter_dir / ".snapshots"
    if not snapshots_dir.exists():
        return []
        
    snapshot_files = sorted(snapshots_dir.glob("snapshot_*.json"), key=lambda f: f.name, reverse=True)
    results = []
    for f in snapshot_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except Exception:
            pass
    return results


class CreateSnapshotRequest(BaseModel):
    title: Optional[str] = ""


@router.post("/api/chapters/{chapter_id}/snapshots")
def create_manual_snapshot(
    chapter_id: str,
    req: CreateSnapshotRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")
        
    final_txt_path = chapter_dir / "chapter_final.txt"
    final_text = ws_server._read_text(final_txt_path)
    
    plan_path = chapter_dir / "plan.json"
    plan = {}
    if plan_path.exists():
        plan = ws_server._read_json(plan_path)
    title = plan.get("chapter_title", req.title or f"第 {safe_id} 章")
    
    snapshot = create_chapter_snapshot(session.root_dir, safe_id, title, final_text, is_manual=True)
    return {"status": "created", "snapshot": snapshot}


@router.post("/api/chapters/{chapter_id}/snapshots/{timestamp}/rollback")
def rollback_chapter_snapshot(
    chapter_id: str,
    timestamp: str,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    import json
    session = coerce_project_session(session)
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    chapter_dir = session.root_dir / "workspace" / "chapters" / f"chapter_{safe_id}"
    if not chapter_dir.exists():
        raise HTTPException(404, f"Chapter {safe_id} not found")
        
    snapshot_file = chapter_dir / ".snapshots" / f"snapshot_{timestamp}.json"
    if not snapshot_file.exists():
        raise HTTPException(404, "Snapshot not found")
        
    try:
        snapshot_data = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except Exception:
         raise HTTPException(500, "Failed to read snapshot file")

    title = str(snapshot_data.get("title") or f"第 {safe_id} 章")
    try:
        document = apply_plain_text_to_manuscript(
            session.root_dir,
            chapter_id=safe_id,
            plain_text=str(snapshot_data.get("final_text") or ""),
            title=title,
            source="restore",
        )
    except DocumentConflictError as exc:
        raise HTTPException(
            409,
            {
                "code": "DOCUMENT_CONFLICT",
                "message": "正文已在其他窗口更新，请刷新后重试。",
                "current": exc.current,
            },
        ) from exc

    return {
        "status": "rolled_back",
        "title": str(document.get("title") or title),
        "revision": int(document["revision"]),
    }

