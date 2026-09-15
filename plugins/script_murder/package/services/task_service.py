"""Persistent, cancellable task orchestration for Script Murder."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..schemas import GenerationTaskRecord, ScriptMurderWorkspace
from .canon_service import CanonService
from .exporter import ScriptMurderExporter
from .playtester import PlaytestService
from .project_service import ProjectService

if TYPE_CHECKING:
    from ..agents.orchestrator import ScriptMurderOrchestrator


class ScriptMurderTaskService:
    """Runs user-triggered generation/audit tasks with durable state."""

    ALLOWED_NODES = {
        "brief",
        "canon",
        "characters",
        "clues",
        "flow",
        "script",
        "host",
        "validate",
        "audit",
        "playtest",
        "export_preflight",
    }

    def __init__(
        self,
        project_svc: ProjectService,
        canon_svc: CanonService,
        orchestrator: ScriptMurderOrchestrator,
        playtest_svc: PlaytestService,
        max_workers: int = 2,
    ) -> None:
        self.project_svc = project_svc
        self.canon_svc = canon_svc
        self.orchestrator = orchestrator
        self.playtest_svc = playtest_svc
        self.db = project_svc.db
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="script-murder")
        self._futures: Dict[str, Future[Any]] = {}
        self._lock = threading.RLock()
        self._apply_lock = threading.RLock()
        self._closed = False

    def submit(self, project_id: str, node: str, params: Optional[Dict[str, Any]] = None) -> GenerationTaskRecord:
        if self._closed:
            raise RuntimeError("Script Murder task service is closed")
        if node not in self.ALLOWED_NODES:
            raise ValueError(f"Unsupported task node: {node}")
        ws = self.project_svc.get_workspace(project_id)
        if not ws:
            raise ValueError(f"Project '{project_id}' not found")
        task_params = dict(params or {})
        task = GenerationTaskRecord(
            id=f"smt_{uuid.uuid4().hex}",
            project_id=project_id,
            node=node,
            input_revision=ws.revision,
            dependency_hash=self.canon_svc.calculate_dependency_hash(ws),
            model=(
                "configured"
                if getattr(self.orchestrator.model_svc, "llm", None)
                or getattr(self.orchestrator.model_svc, "llm_registry", {})
                else "offline"
            ),
            apply_state="pending" if task_params.get("preview_only") else "applied",
        )
        self.db.save_task(task)
        with self._lock:
            self._futures[task.id] = self.executor.submit(self._run, task.id, task_params)
        return task

    def get(self, task_id: str) -> Optional[GenerationTaskRecord]:
        return self.db.get_task(task_id)

    def list(self, project_id: str, limit: int = 100) -> list[GenerationTaskRecord]:
        return self.db.list_tasks(project_id, limit=limit)

    def cancel(self, task_id: str) -> Optional[GenerationTaskRecord]:
        task = self.db.get_task(task_id)
        if not task:
            return None
        if task.status in {"succeeded", "failed", "cancelled", "superseded"}:
            return task
        task.cancel_requested = True
        if task.status == "queued":
            task.status = "cancelled"
            task.finished_at = time.time()
        self.db.save_task(task)
        return task

    def accept(self, task_id: str) -> Optional[GenerationTaskRecord]:
        """Apply a successful preview candidate after a fresh dependency check."""
        task = self.db.get_task(task_id)
        if not task or task.status != "succeeded" or task.apply_state != "pending":
            return task
        with self._apply_lock:
            current = self.project_svc.get_workspace(task.project_id)
            if not current:
                raise ValueError(f"Project '{task.project_id}' not found")
            fresh = current.revision == task.input_revision
            if task.node == "script":
                fresh = self.canon_svc.calculate_dependency_hash(current) == task.dependency_hash
            if not fresh:
                task.status = "superseded"
                task.finished_at = time.time()
                self.db.save_task(task)
                return task
            self._apply_result(task, task.result)
            task.apply_state = "applied"
            self.db.save_task(task)
        return task

    def reject(self, task_id: str) -> Optional[GenerationTaskRecord]:
        """Discard a successful preview candidate without changing workspace data."""
        task = self.db.get_task(task_id)
        if not task or task.status != "succeeded" or task.apply_state != "pending":
            return task
        task.apply_state = "rejected"
        self.db.save_task(task)
        return task

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            for task_id in list(self._futures):
                self.cancel(task_id)
            self.executor.shutdown(wait=False, cancel_futures=False)

    def _update(self, task_id: str, **changes: Any) -> Optional[GenerationTaskRecord]:
        task = self.db.get_task(task_id)
        if not task:
            return None
        for key, value in changes.items():
            setattr(task, key, value)
        self.db.save_task(task)
        return task

    def _run(self, task_id: str, params: Dict[str, Any]) -> None:
        task = self.db.get_task(task_id)
        if not task or task.cancel_requested:
            if task:
                self._update(task_id, status="cancelled", finished_at=time.time())
            return
        self._update(task_id, status="running", started_at=time.time())
        try:
            result = self._execute(task, params)
            latest = self.db.get_task(task_id)
            if not latest:
                return
            if latest.cancel_requested:
                self._update(task_id, status="cancelled", finished_at=time.time(), result=result)
                return
            current = self.project_svc.get_workspace(task.project_id)
            if not current:
                raise ValueError(f"Project '{task.project_id}' not found")
            if current.revision != task.input_revision and task.node not in {"validate", "audit", "playtest", "export_preflight"}:
                # Per-character script jobs may safely commit in parallel as long as
                # their structural dependency fingerprint is unchanged. Any other
                # late writer must be reviewed against the newer aggregate revision.
                same_script_dependency = (
                    task.node == "script"
                    and self.canon_svc.calculate_dependency_hash(current) == task.dependency_hash
                )
                if not same_script_dependency:
                    self._update(task_id, status="superseded", finished_at=time.time(), result=result)
                    return
            if latest.apply_state == "pending":
                self._update(task_id, status="succeeded", finished_at=time.time(), result=result)
                return
            # A workspace aggregate is persisted as one JSON projection today;
            # serialize commits so parallel character jobs cannot lose each
            # other's edits. Recheck structural freshness after waiting.
            with self._apply_lock:
                latest_workspace = self.project_svc.get_workspace(task.project_id)
                if not latest_workspace:
                    raise ValueError(f"Project '{task.project_id}' not found")
                if latest_workspace.revision != task.input_revision and task.node not in {"validate", "audit", "playtest", "export_preflight"}:
                    same_script_dependency = (
                        task.node == "script"
                        and self.canon_svc.calculate_dependency_hash(latest_workspace) == task.dependency_hash
                    )
                    if not same_script_dependency:
                        self._update(task_id, status="superseded", finished_at=time.time(), result=result)
                        return
                self._apply_result(task, result)
            self._update(task_id, status="succeeded", finished_at=time.time(), result=result)
        except Exception as exc:  # task failures are durable and user-visible
            self._update(task_id, status="failed", finished_at=time.time(), error=str(exc))
        finally:
            with self._lock:
                self._futures.pop(task_id, None)

    def _execute(self, task: GenerationTaskRecord, params: Dict[str, Any]) -> Dict[str, Any]:
        ws = self.project_svc.get_workspace(task.project_id)
        if not ws:
            raise ValueError(f"Project '{task.project_id}' not found")
        node = task.node
        if node == "brief":
            return self.orchestrator.generate_brief(str(params.get("inspiration") or ""), ws.meta.player_count)
        if node == "canon":
            return self.orchestrator.generate_truth_canon(str(params.get("inspiration") or ""), ws.meta.player_count).model_dump()
        if node == "characters":
            chars = self.orchestrator.generate_characters(ws.canon, ws.meta.player_count)
            return {"characters": [c.model_dump() for c in chars]}
        if node == "clues":
            clues, conclusions = self.orchestrator.generate_clue_graph(ws.canon, ws.characters)
            return {"clues": [c.model_dump() for c in clues], "conclusions": [c.model_dump() for c in conclusions]}
        if node == "flow":
            return self.orchestrator.generate_game_flow(ws.canon, ws.characters, ws.clues).model_dump()
        if node == "script":
            char_id = str(params.get("character_id") or "")
            char = next((c for c in ws.characters if c.id == char_id), None)
            if not char:
                raise ValueError(f"Character '{char_id}' not found")
            act = int(params.get("act") or 1)
            return {"character_id": char_id, "act": act, "text": self.orchestrator.generate_character_script(char, ws.canon, act)}
        if node == "host":
            return {"host_guide": self.orchestrator.generate_host_guide(ws)}
        if node == "validate":
            from .validator import DeterministicValidator
            return DeterministicValidator(ws).validate_all().model_dump()
        if node == "audit":
            return self.playtest_svc.run_full_audit(ws).model_dump()
        if node == "playtest":
            return self.playtest_svc.run_virtual_playtest(ws).model_dump()
        if node == "export_preflight":
            return ScriptMurderExporter(ws).preflight_check().model_dump()
        raise ValueError(f"Unsupported task node: {node}")

    def _apply_result(self, task: GenerationTaskRecord, result: Dict[str, Any]) -> None:
        node = task.node
        if node in {"validate", "audit", "playtest", "export_preflight"}:
            if node in {"audit", "playtest"}:
                ws = self.project_svc.get_workspace(task.project_id)
                if ws:
                    ws.artifact_status[node] = "current"
                    ws.artifact_status["export"] = "stale"
                    self.project_svc.save_workspace(ws)
            return
        if node == "brief":
            ws = self.project_svc.get_workspace(task.project_id)
            if not ws:
                raise ValueError("Project not found")
            ws.brief = result
            for field in ("title", "era", "setting"):
                if result.get(field):
                    setattr(ws.meta, field, result[field])
            ws.revision += 1
            ws.revisions["brief"] = ws.revisions.get("brief", 0) + 1
            ws.artifact_status.update({k: "stale" for k in ("characters", "clues", "flow", "scripts", "host_guide", "audit", "playtest", "export")})
            self.project_svc.save_workspace(ws)
        elif node == "canon":
            self.canon_svc.update_canon(task.project_id, result)
        elif node == "characters":
            from ..schemas import CharacterProfile
            chars = [CharacterProfile.model_validate(item) for item in result.get("characters", [])]
            self.canon_svc.replace_characters(task.project_id, chars)
        elif node == "clues":
            from ..schemas import ClueItem, DeductiveConclusion
            clues = [ClueItem.model_validate(item) for item in result.get("clues", [])]
            conclusions = [DeductiveConclusion.model_validate(item) for item in result.get("conclusions", [])]
            self.canon_svc.replace_clues(task.project_id, clues, conclusions)
        elif node == "flow":
            self.canon_svc.update_flow(task.project_id, result)
        elif node == "script":
            ws = self.project_svc.get_workspace(task.project_id)
            if not ws:
                raise ValueError("Project not found")
            char = next(c for c in ws.characters if c.id == result["character_id"])
            char.script_acts[f"act_{result['act']}"] = result["text"]
            self.canon_svc.upsert_character(task.project_id, char)
            ws = self.project_svc.get_workspace(task.project_id)
            if ws:
                ws.artifact_status["scripts"] = "current"
                ws.artifact_status["export"] = "stale"
                self.project_svc.save_workspace(ws)
        elif node == "host":
            ws = self.project_svc.get_workspace(task.project_id)
            if not ws:
                raise ValueError("Project not found")
            ws.host_guide = result.get("host_guide", "")
            ws.revision += 1
            ws.revisions["documents"] = ws.revisions.get("documents", 0) + 1
            ws.artifact_status["host_guide"] = "current"
            ws.artifact_status["export"] = "stale"
            self.project_svc.save_workspace(ws)
