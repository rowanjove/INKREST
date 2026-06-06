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

router = APIRouter()


class CreateVersionRequest(BaseModel):
    version_name: str
    note: Optional[str] = ""
    copy_from_active: Optional[bool] = True

class UpdateVersionRequest(BaseModel):
    version_name: Optional[str] = None
    note: Optional[str] = None
    content: Optional[str] = None

class CompareVersionsRequest(BaseModel):
    version_id_a: str
    version_id_b: str

@router.get("/api/chapters/{chapter_id}/versions")
def get_versions(chapter_id: str) -> List[Dict[str, Any]]:
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    versions = store.list_chapter_versions(safe_id)
    
    chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
    final_txt_path = chapter_dir / "chapter_final.txt"
    content = ws_server._read_text(final_txt_path)
    
    plan_path = chapter_dir / "plan.json"
    plan_str = "{}"
    if plan_path.exists():
        try:
            plan_str = plan_path.read_text(encoding="utf-8")
        except Exception:
            pass
            
    if not versions:
        store.save_chapter_version(
            chapter_id=safe_id,
            version_name="版本 A",
            content=content,
            plan=plan_str,
            is_active=True,
            note="历史章节补齐的默认版本"
        )
        versions = store.list_chapter_versions(safe_id)
    else:
        active_version = next((v for v in versions if v.get("is_active") == 1), None)
        if active_version:
            if active_version.get("content") != content:
                store.save_chapter_version(
                    chapter_id=safe_id,
                    version_name=active_version["version_name"],
                    content=content,
                    plan=active_version.get("plan") or plan_str,
                    is_active=True,
                    note=active_version.get("note") or "同步自 chapter_final.txt",
                    version_id=active_version["id"]
                )
                versions = store.list_chapter_versions(safe_id)
        else:
            first_v = versions[0]
            store.save_chapter_version(
                chapter_id=safe_id,
                version_name=first_v["version_name"],
                content=content,
                plan=first_v.get("plan") or plan_str,
                is_active=True,
                note=first_v.get("note") or "同步自 chapter_final.txt",
                version_id=first_v["id"]
            )
            versions = store.list_chapter_versions(safe_id)
            
    return versions

@router.post("/api/chapters/{chapter_id}/versions")
def create_version(chapter_id: str, req: CreateVersionRequest) -> Dict[str, Any]:
    import json
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    
    content = ""
    plan_str = "{}"
    
    if req.copy_from_active:
        versions = store.list_chapter_versions(safe_id)
        active_v = next((v for v in versions if v.get("is_active") == 1), None)
        if active_v:
            content = active_v.get("content", "")
            plan_str = active_v.get("plan", "{}")
        else:
            chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
            final_txt_path = chapter_dir / "chapter_final.txt"
            content = ws_server._read_text(final_txt_path)
            plan_path = chapter_dir / "plan.json"
            if plan_path.exists():
                try:
                    plan_str = plan_path.read_text(encoding="utf-8")
                except Exception:
                    pass
                
    v_id = store.save_chapter_version(
        chapter_id=safe_id,
        version_name=req.version_name,
        content=content,
        plan=plan_str,
        is_active=False,
        note=req.note or ""
    )
    return {"status": "created", "version_id": v_id}

@router.put("/api/chapters/versions/{version_id}")
def update_version(version_id: str, req: UpdateVersionRequest) -> Dict[str, Any]:
    import json
    store = ws_server._get_task_manager().store
    version = store.get_chapter_version(version_id)
    if not version:
        raise HTTPException(404, f"Version {version_id} not found")
        
    name = req.version_name if req.version_name is not None else version["version_name"]
    note = req.note if req.note is not None else version["note"]
    content = req.content if req.content is not None else version["content"]
    
    store.save_chapter_version(
        chapter_id=version["chapter_id"],
        version_name=name,
        content=content,
        plan=version["plan"],
        is_active=bool(version["is_active"]),
        note=note,
        version_id=version_id
    )
    
    if version["is_active"] == 1 and req.content is not None:
        chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{version['chapter_id']}"
        final_txt_path = chapter_dir / "chapter_final.txt"
        final_txt_path.write_text(content, encoding="utf-8")
        
        plan_path = chapter_dir / "plan.json"
        plan = ws_server._read_json(plan_path) if plan_path.exists() else {}
        target_chars = plan.get("target_chars") if isinstance(plan.get("target_chars"), list) else []
        target_min = int(target_chars[0]) if len(target_chars) > 0 and str(target_chars[0]).isdigit() else 0
        target_max = int(target_chars[1]) if len(target_chars) > 1 and str(target_chars[1]).isdigit() else 0
        new_report = wordcount_report(content, target_min, target_max)
        reports_dir = chapter_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "wordcount.json").write_text(json.dumps(new_report, ensure_ascii=False, indent=2), encoding="utf-8")
        
    return {"status": "updated"}

@router.delete("/api/chapters/versions/{version_id}")
def delete_version(version_id: str) -> Dict[str, Any]:
    store = ws_server._get_task_manager().store
    version = store.get_chapter_version(version_id)
    if not version:
        raise HTTPException(404, f"Version {version_id} not found")
        
    try:
        store.delete_chapter_version(version_id)
        return {"status": "deleted"}
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.post("/api/chapters/{chapter_id}/versions/{version_id}/activate")
def activate_version(chapter_id: str, version_id: str) -> Dict[str, Any]:
    import json
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    
    version = store.get_chapter_version(version_id)
    if not version:
        raise HTTPException(404, f"Version {version_id} not found")
    if version["chapter_id"] != safe_id:
        raise HTTPException(400, "Chapter version does not belong to the requested chapter")
        
    try:
        chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
        final_txt_path = chapter_dir / "chapter_final.txt"
        current_text = ws_server._read_text(final_txt_path)
        plan_path = chapter_dir / "plan.json"
        plan = ws_server._read_json(plan_path) if plan_path.exists() else {}
        title = plan.get("chapter_title", f"第 {safe_id} 章")
        create_chapter_snapshot(ws_server.get_root_dir(), safe_id, f"系统自动备份（切换分支前：{title}）", current_text, is_manual=False)
    except Exception as e:
        ws_server.logger.warning("Failed to create pre-activation backup snapshot: %s", e)
        
    store.set_active_chapter_version(safe_id, version_id)
    
    chapter_dir = ws_server.get_root_dir() / "workspace" / "chapters" / f"chapter_{safe_id}"
    final_txt_path = chapter_dir / "chapter_final.txt"
    final_txt_path.write_text(version["content"], encoding="utf-8")
    
    if version.get("plan"):
        try:
            v_plan = json.loads(version["plan"])
            if isinstance(v_plan, dict):
                plan_path = chapter_dir / "plan.json"
                plan_path.write_text(json.dumps(v_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
            
    plan_path = chapter_dir / "plan.json"
    plan = ws_server._read_json(plan_path) if plan_path.exists() else {}
    target_chars = plan.get("target_chars") if isinstance(plan.get("target_chars"), list) else []
    target_min = int(target_chars[0]) if len(target_chars) > 0 and str(target_chars[0]).isdigit() else 0
    target_max = int(target_chars[1]) if len(target_chars) > 1 and str(target_chars[1]).isdigit() else 0
    new_report = wordcount_report(version["content"], target_min, target_max)
    reports_dir = chapter_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "wordcount.json").write_text(json.dumps(new_report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"status": "activated", "title": plan.get("chapter_title", f"第 {safe_id} 章")}

@router.post("/api/chapters/{chapter_id}/versions/compare")
def compare_versions(chapter_id: str, req: CompareVersionsRequest) -> List[Dict[str, str]]:
    safe_id = ws_server._validate_id(chapter_id, "chapter_id")
    store = ws_server._get_task_manager().store
    v_a = store.get_chapter_version(req.version_id_a)
    v_b = store.get_chapter_version(req.version_id_b)
    if not v_a or not v_b:
        raise HTTPException(404, "One or both versions not found for diff comparison")
    if v_a["chapter_id"] != safe_id or v_b["chapter_id"] != safe_id:
        raise HTTPException(400, "Versions must belong to the requested chapter")
        
    from novel_agent.utils.diff import compute_text_diff
    return compute_text_diff(v_a["content"], v_b["content"])

