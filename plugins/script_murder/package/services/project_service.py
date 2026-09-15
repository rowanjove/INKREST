"""Project management service for Script Murder."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from ..database import DatabaseManager
from ..schemas import ProjectMeta, ScriptMurderWorkspace


class ProjectService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def list_projects(self) -> List[Dict[str, Any]]:
        return self.db.list_projects()

    def create_project(self, payload: Dict[str, Any]) -> ScriptMurderWorkspace:
        project_id = str(payload.get("id") or f"sm_{uuid.uuid4().hex[:8]}")
        meta = ProjectMeta(
            id=project_id,
            title=payload.get("title") or "未命名剧本",
            player_count=int(payload.get("player_count", 6)),
            duration_minutes=int(payload.get("duration_minutes", 240)),
            genre=payload.get("genre") or ["本格推理"],
            tone=payload.get("tone") or ["冷峻", "写实"],
            era=payload.get("era") or "1998年",
            setting=payload.get("setting") or "北方沿海港口城市",
            difficulty=int(payload.get("difficulty", 4)),
            style=payload.get("style") or "hardcore",
            status="planning",
        )
        return self.db.create_project(meta)

    def get_workspace(self, project_id: str) -> Optional[ScriptMurderWorkspace]:
        return self.db.load_workspace(project_id)

    def save_workspace(self, workspace: ScriptMurderWorkspace) -> None:
        self.db.save_workspace(workspace)

    def delete_project(self, project_id: str) -> bool:
        return self.db.delete_project(project_id)

    def create_snapshot(self, project_id: str, label: str) -> str:
        return self.db.create_snapshot(project_id, label)

    def list_snapshots(self, project_id: str) -> List[Dict[str, Any]]:
        return self.db.list_snapshots(project_id)

    def restore_snapshot(self, project_id: str, snapshot_id: str) -> ScriptMurderWorkspace:
        return self.db.restore_snapshot(project_id, snapshot_id)
