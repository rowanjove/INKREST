"""Project manager for handling novel projects."""

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from web.helpers import _copy_default_assets, _copy_default_prompts, _write_yaml

logger = logging.getLogger("web.project_manager")

MAX_PINNED_PROJECTS = 10


class ProjectManager:
    """Manages multiple novel projects."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.registry_path = base_dir / "projects.json"

    def _read_registry(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            return {"projects": {}, "active_id": None}
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"projects": {}, "active_id": None}
        if not isinstance(data.get("projects"), dict):
            data["projects"] = {}
        if data.get("active_id") and data["projects"].get(data["active_id"]) is None:
            data["active_id"] = None
            self._write_registry(data)
        return data

    def _write_registry(self, data: Dict[str, Any]) -> None:
        self.registry_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _iso_to_epoch(iso: str) -> float:
        if not iso:
            return 0.0
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    def _project_activity_epoch(self, project_dir: Path, info: Dict[str, Any]) -> float:
        epochs: List[float] = []
        reg_ts = self._iso_to_epoch(str(info.get("updated_at") or ""))
        if reg_ts:
            epochs.append(reg_ts)

        outline_path = project_dir / "workspace" / "outline.json"
        if outline_path.is_file():
            epochs.append(outline_path.stat().st_mtime)

        db_path = project_dir / "data" / "novel.sqlite"
        if db_path.is_file():
            epochs.append(db_path.stat().st_mtime)

        snapshot_path = project_dir / "workspace" / "reports" / "progress_snapshot.json"
        if snapshot_path.is_file():
            epochs.append(snapshot_path.stat().st_mtime)

        cover_dir = project_dir
        for suffix in (".jpg", ".png", ".webp"):
            cover = cover_dir / f"cover{suffix}"
            if cover.is_file():
                epochs.append(cover.stat().st_mtime)

        return max(epochs) if epochs else 0.0

    def touch_activity(self, pid: str) -> None:
        """Record project edit time in registry (for library sort)."""
        data = self._read_registry()
        proj = data.get("projects", {}).get(pid)
        if not proj:
            return
        proj["updated_at"] = datetime.now().isoformat()
        self._write_registry(data)

    def set_pinned(self, pid: str, pinned: bool) -> Dict[str, Any]:
        data = self._read_registry()
        projects = data.get("projects", {})
        if pid not in projects:
            raise HTTPException(404, f"Project {pid} not found")

        proj = projects[pid]
        if pinned:
            if not proj.get("pinned"):
                pinned_count = sum(1 for p in projects.values() if p.get("pinned"))
                if pinned_count >= MAX_PINNED_PROJECTS:
                    raise HTTPException(
                        400,
                        f"最多置顶 {MAX_PINNED_PROJECTS} 本书，请先取消其它置顶",
                    )
            proj["pinned"] = True
            proj["pinned_at"] = datetime.now().isoformat()
        else:
            proj.pop("pinned", None)
            proj.pop("pinned_at", None)

        self._write_registry(data)
        return {
            "id": pid,
            "pinned": bool(proj.get("pinned")),
            "pinned_at": proj.get("pinned_at"),
            "pinned_limit": MAX_PINNED_PROJECTS,
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        data = self._read_registry()
        projects: List[Dict[str, Any]] = []
        for pid, info in data.get("projects", {}).items():
            project_dir = self.base_dir / "projects" / pid
            try:
                from novel_agent.services.project_library_stats import project_library_stats

                chapter_count, total_words = project_library_stats(project_dir)
            except Exception as exc:
                logger.warning("Failed to load library stats for %s: %s", pid, exc)
                chapter_count, total_words = 0, 0
            meta_path = project_dir / "config" / "project_meta.json"
            meta: Dict[str, Any] = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to load project metadata from %s: %s", meta_path, exc)

            activity_epoch = self._project_activity_epoch(project_dir, info)
            activity_at = (
                datetime.fromtimestamp(activity_epoch).isoformat()
                if activity_epoch
                else info.get("updated_at", "")
            )

            pending_alert_count = 0
            try:
                from novel_agent.services.pipeline_pending import count_pipeline_alerts_cached

                pending_alert_count = count_pipeline_alerts_cached(project_dir)
            except Exception as exc:
                logger.warning(
                    "Failed to count pipeline alerts for %s: %s", pid, exc
                )
                pending_alert_count = 0

            projects.append({
                "id": pid,
                "name": info.get("name", pid),
                "description": info.get("description", ""),
                "created_at": info.get("created_at", ""),
                "updated_at": info.get("updated_at", ""),
                "activity_at": activity_at,
                "pinned": bool(info.get("pinned")),
                "pinned_at": info.get("pinned_at") or "",
                "chapter_count": chapter_count,
                "total_words": total_words,
                "genre": meta.get("genre", ""),
                "channel": meta.get("channel", ""),
                "target_chapters": meta.get("target_chapters", 0),
                "has_cover": any((project_dir / f"cover{suffix}").exists() for suffix in (".jpg", ".png", ".webp")),
                "pending_alert_count": pending_alert_count,
            })

        def sort_key(item: Dict[str, Any]) -> tuple:
            if item.get("pinned"):
                return (0, -self._iso_to_epoch(str(item.get("pinned_at") or "")))
            act = item.get("activity_at") or item.get("updated_at") or ""
            return (1, -self._iso_to_epoch(str(act)))

        projects.sort(key=sort_key)
        return projects

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        pid = uuid.uuid4().hex[:8]
        project_dir = self.base_dir / "projects" / pid
        project_dir.mkdir(parents=True, exist_ok=True)

        for d in ("config", "state", "assets", "prompts", "workspace/chapters", "dashboard"):
            (project_dir / d).mkdir(parents=True, exist_ok=True)

        _copy_default_assets(project_dir / "assets")
        _copy_default_prompts(project_dir / "prompts")

        config_path = project_dir / "config" / "pipeline.yaml"
        if not config_path.exists():
            # llm / embedding live in repo config/pipeline.yaml (global for all books).
            _write_yaml(
                config_path,
                {
                    "chapter": {
                        "default_target_chars": [2000, 3000],
                        "default_scene_target_chars": [400, 800],
                    },
                    "runtime": {"max_workers": 4, "retry_attempts": 1, "interactive": False},
                },
            )

        now = datetime.now().isoformat()
        data = self._read_registry()
        if "projects" not in data:
            data["projects"] = {}
        data["projects"][pid] = {
            "name": name,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "pinned": False,
        }
        self._write_registry(data)

        return {"id": pid, "name": name, "description": description}

    def delete_project(self, pid: str) -> None:
        data = self._read_registry()
        if pid not in data.get("projects", {}):
            raise HTTPException(404, f"Project {pid} not found")
        project_dir = self.base_dir / "projects" / pid
        if project_dir.exists():
            shutil.rmtree(project_dir)
        del data["projects"][pid]
        if data.get("active_id") == pid:
            data["active_id"] = None
        self._write_registry(data)

    def switch_project(self, pid: str) -> Dict[str, Any]:
        data = self._read_registry()
        if pid not in data.get("projects", {}):
            raise HTTPException(404, f"Project {pid} not found")
        data["active_id"] = pid
        self._write_registry(data)
        return {"id": pid, "name": data["projects"][pid]["name"]}

    def get_active_id(self) -> Optional[str]:
        data = self._read_registry()
        active_id = data.get("active_id")
        if active_id and active_id in data.get("projects", {}):
            return active_id
        return None

    def migrate_legacy(self) -> str:
        pid = "default"
        project_dir = self.base_dir / "projects" / pid
        project_dir.mkdir(parents=True, exist_ok=True)

        dirs_to_move = ["state", "data", "config", "assets", "prompts", "workspace", "dashboard"]
        for d in dirs_to_move:
            src = self.base_dir / d
            dst = project_dir / d
            if src.exists() and not dst.exists():
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        prompts_dir = project_dir / "prompts"
        defaults_dir = prompts_dir / "defaults"
        if not defaults_dir.exists():
            defaults_dir.mkdir(parents=True, exist_ok=True)
            for f in prompts_dir.glob("*.md"):
                if f.parent == defaults_dir:
                    continue
                shutil.copy2(f, defaults_dir / f.name)

        now = datetime.now().isoformat()
        registry = {
            "projects": {
                pid: {
                    "name": "默认小说",
                    "description": "从旧版数据自动迁移",
                    "created_at": now,
                    "updated_at": now,
                }
            },
            "active_id": pid,
        }
        self._write_registry(registry)
        return pid