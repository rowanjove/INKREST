import json
import uuid
import zipfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

import web.context as ws_server
from web.project_manager import MAX_PINNED_PROJECTS

router = APIRouter()

import web.routes.projects as projects_module
UPLOAD_CHUNK_BYTES = 1024 * 1024
BLOCKED_PROJECT_ARCHIVE_PARTS = {"plugins", "__pycache__"}
BLOCKED_PROJECT_ARCHIVE_SUFFIXES = {
    ".py", ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".bat", ".cmd",
    ".com", ".msi", ".ps1", ".sh", ".js", ".vbs", ".jar",
}
SENSITIVE_PROJECT_ARCHIVE_PARTS = {"logs", ".git"}
SENSITIVE_PROJECT_ARCHIVE_PATHS = {
    "config/models.json",
    "config/pipeline.yaml",
    "config/pipeline.yml",
}
SENSITIVE_PROJECT_ARCHIVE_NAMES = {
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}
SENSITIVE_PROJECT_ARCHIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def _copy_upload_with_limit(source, destination, limit: int) -> None:
    total = 0
    while True:
        chunk = source.read(UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, "Project ZIP exceeds the upload size limit")
        destination.write(chunk)


def _reject_executable_archive_member(filename: str) -> None:
    member = Path(filename.replace("\\", "/"))
    lowered_parts = {part.lower() for part in member.parts}
    if lowered_parts & BLOCKED_PROJECT_ARCHIVE_PARTS:
        raise HTTPException(400, f"Project ZIP contains executable content: {filename}")
    if member.suffix.lower() in BLOCKED_PROJECT_ARCHIVE_SUFFIXES:
        raise HTTPException(400, f"Project ZIP contains executable content: {filename}")


def _is_executable_archive_member(filename: str) -> bool:
    try:
        _reject_executable_archive_member(filename)
        return False
    except HTTPException:
        return True


def _is_sensitive_archive_member(filename: str) -> bool:
    member = Path(filename.replace("\\", "/"))
    parts = tuple(part.lower() for part in member.parts)
    normalized = "/".join(parts)
    name = member.name.lower()
    if set(parts) & SENSITIVE_PROJECT_ARCHIVE_PARTS:
        return True
    if normalized in SENSITIVE_PROJECT_ARCHIVE_PATHS:
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SENSITIVE_PROJECT_ARCHIVE_NAMES:
        return True
    if member.suffix.lower() in SENSITIVE_PROJECT_ARCHIVE_SUFFIXES:
        return True
    return False


def _should_export_project_member(filename: str) -> bool:
    return not (
        filename == "project_info.json"
        or _is_executable_archive_member(filename)
        or _is_sensitive_archive_member(filename)
    )


def _extract_and_validate_zip(tmp_path: Path, project_dir: Path) -> None:
    with zipfile.ZipFile(tmp_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > projects_module.MAX_PROJECT_ZIP_FILES:
            raise HTTPException(413, "Project ZIP contains too many files")
        if sum(info.file_size for info in infos) > projects_module.MAX_PROJECT_ZIP_UNCOMPRESSED_BYTES:
            raise HTTPException(413, "Project ZIP expands beyond the allowed size")
        
        resolved_dest = project_dir.resolve()
        for info in infos:
            _reject_executable_archive_member(info.filename)
            member_path = (project_dir / info.filename).resolve()
            if resolved_dest not in member_path.parents and member_path != resolved_dest:
                raise HTTPException(400, f"Zip member attempts directory traversal: {info.filename}")
        
        # 安全地逐个解包到已验证的物理绝对路径，规避 extractall 二次解析路径导致的防御绕过
        import shutil
        for info in infos:
            member_path = (project_dir / info.filename).resolve()
            if info.is_dir():
                member_path.mkdir(parents=True, exist_ok=True)
            else:
                member_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(member_path, "wb") as target:
                    shutil.copyfileobj(source, target)


def _parse_imported_project_metadata(project_dir: Path) -> Tuple[str, str, bool, str]:
    info_path = project_dir / "project_info.json"
    name = "导入的小说"
    description = "通过项目包导入"
    import_pinned = False
    import_pinned_at = ""

    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            name = info.get("name", name)
            description = info.get("description", description)
            import_pinned = bool(info.get("pinned"))
            import_pinned_at = str(info.get("pinned_at") or "")
            info_path.unlink()
        except Exception:
            pass
    else:
        outline_path = project_dir / "workspace" / "outline.json"
        if outline_path.exists():
            try:
                outline = json.loads(outline_path.read_text(encoding="utf-8"))
                name = outline.get("chosen_title") or (outline.get("title_options")[0] if outline.get("title_options") else name)
            except Exception:
                pass
    return name, description, import_pinned, import_pinned_at


def _register_imported_project(pid: str, name: str, description: str, import_pinned: bool, import_pinned_at: str) -> None:
    now = datetime.now().isoformat()
    entry: Dict[str, Any] = {
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
    }
    if import_pinned:
        registry = ws_server.project_manager._read_registry()
        pinned_count = sum(1 for p in registry.get("projects", {}).values() if p.get("pinned"))
        if pinned_count < MAX_PINNED_PROJECTS:
            entry["pinned"] = True
            entry["pinned_at"] = import_pinned_at or now
    ws_server.project_manager.register_project(pid, entry)


class BatchExportRequest(BaseModel):
    project_ids: List[str]


# ---- API Endpoints ----

@router.post("/api/projects/batch-export-zip")
def batch_export_projects_zip(req: BatchExportRequest) -> FileResponse:
    if not req.project_ids:
        raise HTTPException(400, "project_ids is required")
    if len(req.project_ids) > 20:
        raise HTTPException(400, "A single batch export supports at most 20 projects")

    data = ws_server.project_manager._read_registry()
    projects = data.get("projects", {})
    unique_ids: List[str] = []
    for pid in req.project_ids:
        ws_server._validate_id(pid, "project_id")
        if pid not in projects:
            raise HTTPException(404, f"Project {pid} not found")
        if pid not in unique_ids:
            unique_ids.append(pid)

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False, prefix="studio_batch_export_")
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "exported_at": datetime.now().isoformat(),
                "project_ids": unique_ids,
                "count": len(unique_ids),
            }
            zf.writestr("batch_export_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for pid in unique_ids:
                project_dir = ws_server.BASE_DIR / "projects" / pid
                info = projects.get(pid, {})
                info_data = {
                    "name": info.get("name", pid),
                    "description": info.get("description", ""),
                    "pinned": bool(info.get("pinned")),
                    "pinned_at": info.get("pinned_at") or "",
                    "exported_at": datetime.now().isoformat(),
                }
                zf.writestr(
                    f"{pid}/project_info.json",
                    json.dumps(info_data, ensure_ascii=False, indent=2),
                )
                for path in project_dir.rglob("*"):
                    if not path.is_file() or path.is_symlink():
                        continue
                    try:
                        path.resolve().relative_to(project_dir.resolve())
                    except ValueError:
                        continue
                    rel_path = path.relative_to(project_dir).as_posix()
                    if not _should_export_project_member(rel_path):
                        continue
                    zf.write(str(path), f"{pid}/{rel_path}")
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Batch export failed: {exc}") from exc

    return FileResponse(
        str(tmp_path),
        filename="inkrest-studio-batch-export.zip",
        media_type="application/octet-stream",
        background=BackgroundTask(tmp_path.unlink, missing_ok=True),
    )


@router.get("/api/projects/{pid}/export-zip")
def export_project_zip(pid: str) -> FileResponse:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, f"Project {pid} not found")

    data = ws_server.project_manager._read_registry()
    info = data.get("projects", {}).get(pid, {})
    project_name = info.get("name", pid)

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False, prefix="project_export_")
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            info_data = {
                "name": info.get("name", pid),
                "description": info.get("description", ""),
                "pinned": bool(info.get("pinned")),
                "pinned_at": info.get("pinned_at") or "",
                "exported_at": datetime.now().isoformat(),
            }
            zf.writestr("project_info.json", json.dumps(info_data, ensure_ascii=False, indent=2))

            for path in project_dir.rglob("*"):
                if path.is_file():
                    if path.is_symlink():
                        continue
                    try:
                        path.resolve().relative_to(project_dir.resolve())
                    except ValueError:
                        continue
                    rel_path = path.relative_to(project_dir)
                    rel_posix = rel_path.as_posix()
                    if not _should_export_project_member(rel_posix):
                        continue
                    zf.write(str(path), rel_posix)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Exporting ZIP failed: {exc}")

    safe_filename = "".join(c for c in project_name if c.isalnum() or c in (" ", "_", "-")).strip()
    if not safe_filename:
        safe_filename = pid
    filename = f"{safe_filename}.zip"

    return FileResponse(
        str(tmp_path),
        filename=filename,
        media_type="application/octet-stream",
        background=BackgroundTask(tmp_path.unlink, missing_ok=True),
    )


@router.post("/api/projects/import-zip")
def import_project_zip(file: UploadFile = File(...)) -> Dict[str, Any]:
    pid = uuid.uuid4().hex[:8]
    project_dir = ws_server.BASE_DIR / "projects" / pid
    project_dir.mkdir(parents=True, exist_ok=True)

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        with open(tmp_path, "wb") as f:
            _copy_upload_with_limit(file.file, f, projects_module.MAX_PROJECT_ZIP_BYTES)

        _extract_and_validate_zip(tmp_path, project_dir)
        name, description, import_pinned, import_pinned_at = _parse_imported_project_metadata(project_dir)
        _register_imported_project(pid, name, description, import_pinned, import_pinned_at)

        return {"id": pid, "name": name, "description": description, "status": "imported"}

    except HTTPException:
        if project_dir.exists():
            shutil.rmtree(project_dir)
        raise
    except Exception as exc:
        if project_dir.exists():
            shutil.rmtree(project_dir)
        raise HTTPException(500, f"Importing ZIP failed: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/api/projects/{pid}/export-serial")
def export_serial(pid: str, format: str = "zip") -> Any:
    ws_server._validate_id(pid, "project_id")
    project_dir = ws_server.BASE_DIR / "projects" / pid
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
        
    chapters = []
    ws_dir = project_dir / "workspace"
    chapters_dir = ws_dir / "chapters"
    if chapters_dir.exists():
        for ch_dir in sorted(list(chapters_dir.glob("chapter_*")), key=lambda d: d.name):
            ch_id = ch_dir.name.replace("chapter_", "")
            txt_path = ch_dir / "chapter_final.txt"
            plan_path = ch_dir / "plan.json"
            
            title = f"第 {ch_id} 章"
            if plan_path.exists():
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    title = plan.get("chapter_title", title)
                except (OSError, json.JSONDecodeError):
                    pass
                    
            if txt_path.exists():
                try:
                    text = txt_path.read_text(encoding="utf-8").strip()
                    if text:
                        chapters.append((ch_id, title, text))
                except OSError:
                    pass
                    
    if not chapters:
        raise HTTPException(400, "当前项目还没有任何已生成的章节")
        
    if format == "zip":
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False, prefix="serial_export_")
        tmp_path = Path(tmp.name)
        tmp.close()
        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for ch_id, title, text in chapters:
                    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
                    zf.writestr(f"chapter_{ch_id}_{safe_title}.txt", text)
            return FileResponse(
                str(tmp_path),
                filename="serial_chapters.zip",
                media_type="application/octet-stream",
                background=BackgroundTask(tmp_path.unlink, missing_ok=True)
            )
        except Exception as e:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(500, f"Export ZIP failed: {e}")
            
    else:
        txt_lines = []
        for ch_id, title, text in chapters:
            txt_lines.append(f"### {title}\n\n{text}\n\n")
        full_text = "\n".join(txt_lines)
        
        tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8", prefix="serial_txt_")
        tmp_path = Path(tmp.name)
        tmp.write(full_text)
        tmp.close()
        
        return FileResponse(
            str(tmp_path),
            filename="serial_all_chapters.txt",
            media_type="text/plain",
            background=BackgroundTask(tmp_path.unlink, missing_ok=True)
        )
