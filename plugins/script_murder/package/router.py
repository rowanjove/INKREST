"""FastAPI router for Script Murder Studio."""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from .agents.orchestrator import ScriptMurderOrchestrator
from .schemas import (
    CharacterProfile,
    ClueItem,
    GameFlow,
    TruthCanon,
    TruthFact,
)
from .services import (
    CanonService,
    DeterministicValidator,
    PlaytestService,
    ProjectService,
    ScriptMurderExporter,
    ScriptMurderTaskService,
)


class CreateProjectRequest(BaseModel):
    title: str
    player_count: int = 6
    duration_minutes: int = 240
    genre: List[str] = Field(default_factory=lambda: ["本格推理"])
    era: str = "1998年"
    setting: str = "北方沿海港口城市"
    difficulty: int = 4
    style: str = "hardcore"


class InspirationRequest(BaseModel):
    inspiration: str
    player_count: Optional[int] = None


class SnapshotRequest(BaseModel):
    label: str = "手动快照"


class TaskRequest(BaseModel):
    node: str
    params: Dict[str, Any] = Field(default_factory=dict)


def create_router(
    project_svc: ProjectService,
    canon_svc: CanonService,
    orchestrator: ScriptMurderOrchestrator,
    playtest_svc: PlaytestService,
    task_svc: Optional[ScriptMurderTaskService] = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/ext/script-murder", tags=["script_murder"])

    def require_task_service() -> ScriptMurderTaskService:
        if task_svc is None:
            raise HTTPException(503, "插件任务服务尚未启动")
        return task_svc

    # -----------------------------------------------------------------------
    # Projects CRUD
    # -----------------------------------------------------------------------
    @router.get("/projects")
    def list_projects() -> List[Dict[str, Any]]:
        return project_svc.list_projects()

    @router.post("/projects")
    def create_project(req: CreateProjectRequest) -> Dict[str, Any]:
        ws = project_svc.create_project(req.model_dump())
        return ws.model_dump()

    @router.get("/projects/{project_id}")
    def get_project(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        return ws.model_dump()

    @router.get("/projects/{project_id}/workspace")
    def get_workspace(project_id: str) -> Dict[str, Any]:
        return get_project(project_id)

    @router.get("/projects/{project_id}/truth")
    def get_truth(project_id: str) -> Dict[str, Any]:
        return {"canon": get_project(project_id)["canon"]}

    @router.get("/projects/{project_id}/characters")
    def list_characters(project_id: str) -> Dict[str, Any]:
        return {"characters": get_project(project_id)["characters"]}

    @router.get("/projects/{project_id}/clues")
    def list_clues(project_id: str) -> Dict[str, Any]:
        payload = get_project(project_id)
        return {"clues": payload["clues"], "conclusions": payload["conclusions"]}

    @router.get("/projects/{project_id}/flow")
    def get_flow(project_id: str) -> Dict[str, Any]:
        return {"flow": get_project(project_id)["flow"]}

    @router.delete("/projects/{project_id}")
    def delete_project(project_id: str) -> Dict[str, Any]:
        if not project_svc.delete_project(project_id):
            raise HTTPException(404, f"Project '{project_id}' not found")
        return {"status": "ok", "deleted": project_id}

    @router.get("/trash")
    def list_trash() -> Dict[str, Any]:
        return {"projects": project_svc.db.list_deleted_projects()}

    @router.post("/trash/{trash_id}/restore")
    def restore_trash(trash_id: str) -> Dict[str, Any]:
        try:
            restored = project_svc.db.restore_deleted_project(trash_id)
            if not restored:
                raise HTTPException(404, "Trash project not found")
            return {"status": "ok", "restored": restored}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    # -----------------------------------------------------------------------
    # Canon & Facts
    # -----------------------------------------------------------------------
    @router.put("/projects/{project_id}/canon")
    def update_canon(project_id: str, canon: TruthCanon) -> Dict[str, Any]:
        try:
            updated = canon_svc.update_canon(project_id, canon.model_dump())
            return updated.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/projects/{project_id}/facts")
    def add_fact(project_id: str, fact: TruthFact) -> Dict[str, Any]:
        try:
            added = canon_svc.add_fact(project_id, fact)
            return added.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    # -----------------------------------------------------------------------
    # Characters
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/characters")
    @router.put("/projects/{project_id}/characters/{char_id}")
    def upsert_character(project_id: str, char: CharacterProfile, char_id: Optional[str] = None) -> Dict[str, Any]:
        if char_id:
            char.id = char_id
        try:
            saved = canon_svc.upsert_character(project_id, char)
            return saved.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.delete("/projects/{project_id}/characters/{char_id}")
    def delete_character(project_id: str, char_id: str) -> Dict[str, Any]:
        try:
            if not canon_svc.delete_character(project_id, char_id):
                raise HTTPException(404, f"Character '{char_id}' not found")
            return {"status": "ok", "deleted": char_id}
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    # -----------------------------------------------------------------------
    # Clues
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/clues")
    @router.put("/projects/{project_id}/clues/{clue_id}")
    def upsert_clue(project_id: str, clue: ClueItem, clue_id: Optional[str] = None) -> Dict[str, Any]:
        if clue_id:
            clue.id = clue_id
        try:
            saved = canon_svc.upsert_clue(project_id, clue)
            return saved.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.delete("/projects/{project_id}/clues/{clue_id}")
    def delete_clue(project_id: str, clue_id: str) -> Dict[str, Any]:
        try:
            if not canon_svc.delete_clue(project_id, clue_id):
                raise HTTPException(404, f"Clue '{clue_id}' not found")
            return {"status": "ok", "deleted": clue_id}
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    # -----------------------------------------------------------------------
    # Flow
    # -----------------------------------------------------------------------
    @router.put("/projects/{project_id}/flow")
    def update_flow(project_id: str, flow: GameFlow) -> Dict[str, Any]:
        try:
            updated = canon_svc.update_flow(project_id, flow.model_dump())
            return updated.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    # -----------------------------------------------------------------------
    # AI Generation Pipeline
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/ai/brief")
    def ai_generate_brief(project_id: str, req: InspirationRequest) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        count = req.player_count or ws.meta.player_count
        brief = orchestrator.generate_brief(req.inspiration, count)
        ws.meta.title = brief.get("title", ws.meta.title)
        ws.meta.era = brief.get("era", ws.meta.era)
        ws.meta.setting = brief.get("setting", ws.meta.setting)
        project_svc.save_workspace(ws)
        return brief

    @router.post("/projects/{project_id}/ai/run")
    def submit_ai_task(project_id: str, req: TaskRequest) -> Dict[str, Any]:
        try:
            task = require_task_service().submit(project_id, req.node, req.params)
            return {"task": task.model_dump()}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.get("/projects/{project_id}/ai/tasks")
    def list_ai_tasks(project_id: str) -> Dict[str, Any]:
        try:
            return {"tasks": [t.model_dump() for t in require_task_service().list(project_id)]}
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/projects/{project_id}/ai/tasks/{task_id}")
    def get_ai_task(project_id: str, task_id: str) -> Dict[str, Any]:
        task = require_task_service().get(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(404, "Task not found")
        return {"task": task.model_dump()}

    @router.post("/projects/{project_id}/ai/tasks/{task_id}/cancel")
    def cancel_ai_task(project_id: str, task_id: str) -> Dict[str, Any]:
        svc = require_task_service()
        task = svc.get(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(404, "Task not found")
        cancelled = svc.cancel(task_id)
        return {"task": cancelled.model_dump() if cancelled else {}}

    @router.post("/projects/{project_id}/ai/tasks/{task_id}/accept")
    def accept_ai_task(project_id: str, task_id: str) -> Dict[str, Any]:
        svc = require_task_service()
        task = svc.get(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(404, "Task not found")
        try:
            accepted = svc.accept(task_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"task": accepted.model_dump() if accepted else {}}

    @router.post("/projects/{project_id}/ai/tasks/{task_id}/reject")
    def reject_ai_task(project_id: str, task_id: str) -> Dict[str, Any]:
        svc = require_task_service()
        task = svc.get(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(404, "Task not found")
        rejected = svc.reject(task_id)
        return {"task": rejected.model_dump() if rejected else {}}

    @router.post("/projects/{project_id}/ai/canon")
    def ai_generate_canon(project_id: str, req: InspirationRequest) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        canon = orchestrator.generate_truth_canon(req.inspiration, ws.meta.player_count)
        canon_svc.update_canon(project_id, canon.model_dump())
        return canon.model_dump()

    @router.post("/projects/{project_id}/ai/characters")
    def ai_generate_characters(project_id: str) -> List[Dict[str, Any]]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        characters = orchestrator.generate_characters(ws.canon, ws.meta.player_count)
        for char in characters:
            canon_svc.upsert_character(project_id, char)
        return [c.model_dump() for c in characters]

    @router.post("/projects/{project_id}/ai/clues")
    def ai_generate_clues(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        clues, conclusions = orchestrator.generate_clue_graph(ws.canon, ws.characters)
        for c in clues:
            canon_svc.upsert_clue(project_id, c)
        for cn in conclusions:
            canon_svc.upsert_conclusion(project_id, cn)
        return {
            "clues": [c.model_dump() for c in clues],
            "conclusions": [cn.model_dump() for cn in conclusions],
        }

    @router.post("/projects/{project_id}/ai/flow")
    def ai_generate_flow(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        flow = orchestrator.generate_game_flow(ws.canon, ws.characters, ws.clues)
        canon_svc.update_flow(project_id, flow.model_dump())
        return flow.model_dump()

    @router.post("/projects/{project_id}/ai/script/{char_id}")
    def ai_generate_script(project_id: str, char_id: str, act: int = 1) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        char = next((c for c in ws.characters if c.id == char_id), None)
        if not char:
            raise HTTPException(404, f"Character '{char_id}' not found")
        script_text = orchestrator.generate_character_script(char, ws.canon, act)
        char.script_acts[f"act_{act}"] = script_text
        canon_svc.upsert_character(project_id, char)
        return {"character_id": char_id, f"act_{act}": script_text}

    @router.post("/projects/{project_id}/ai/host")
    def ai_generate_host(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        guide_text = orchestrator.generate_host_guide(ws)
        ws.host_guide = guide_text
        project_svc.save_workspace(ws)
        return {"host_guide": guide_text}

    # -----------------------------------------------------------------------
    # Deterministic Validation & Playtest
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/validate")
    def run_validation(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        validator = DeterministicValidator(ws)
        report = validator.validate_all()
        return report.model_dump()

    @router.post("/projects/{project_id}/audit/semantic")
    def run_semantic_audit(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        report = playtest_svc.run_full_audit(ws)
        return report.model_dump()

    @router.post("/projects/{project_id}/playtest")
    def run_playtest(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        report = playtest_svc.run_virtual_playtest(ws)
        return report.model_dump()

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/export")
    def submit_export(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        preflight = ScriptMurderExporter(ws).preflight_check()
        if not preflight.can_export:
            raise HTTPException(409, detail=preflight.model_dump())
        return {
            "status": "ready",
            "download_url": f"/api/ext/script-murder/projects/{project_id}/export/download",
            "preflight": preflight.model_dump(),
        }

    @router.get("/projects/{project_id}/documents")
    def list_documents(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        return {
            "documents": ws.documents,
            "host_guide": ws.host_guide,
            "artifact_status": ws.artifact_status,
            "revision": ws.revision,
        }

    @router.get("/projects/{project_id}/export/preflight")
    def export_preflight(project_id: str) -> Dict[str, Any]:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        exporter = ScriptMurderExporter(ws)
        return exporter.preflight_check().model_dump()

    @router.get("/projects/{project_id}/export/download")
    def export_download(project_id: str) -> Response:
        ws = project_svc.get_workspace(project_id)
        if not ws:
            raise HTTPException(404, f"Project '{project_id}' not found")
        exporter = ScriptMurderExporter(ws)
        try:
            zip_bytes = exporter.build_zip_bytes()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

        title = ws.meta.title or "script_murder"
        from urllib.parse import quote
        safe_filename = f"{quote(title, safe='')}_剧本杀完整开本包.zip"

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
            },
        )

    # -----------------------------------------------------------------------
    # Snapshots
    # -----------------------------------------------------------------------
    @router.post("/projects/{project_id}/snapshots")
    def create_snapshot(project_id: str, req: SnapshotRequest) -> Dict[str, Any]:
        try:
            sid = project_svc.create_snapshot(project_id, req.label)
            return {"status": "ok", "snapshot_id": sid}
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/projects/{project_id}/snapshots")
    def list_snapshots(project_id: str) -> List[Dict[str, Any]]:
        return project_svc.list_snapshots(project_id)

    @router.post("/projects/{project_id}/snapshots/{snapshot_id}/restore")
    def restore_snapshot(project_id: str, snapshot_id: str) -> Dict[str, Any]:
        try:
            ws = project_svc.restore_snapshot(project_id, snapshot_id)
            return ws.model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    return router
