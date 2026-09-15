"""Run Tracker for ShanShan Assistant tool executions and step trace."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import RunRecord, ToolCallStep


class RunTracker:
    def __init__(self, store: Optional[AssistantStore] = None):
        self.store = store
        self._active_runs: Dict[str, RunRecord] = {}
        self._start_times: Dict[str, float] = {}

    def start_run(
        self,
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        model_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> RunRecord:
        rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
        record = RunRecord(
            id=rid,
            thread_id=thread_id,
            project_id=project_id,
            skill_id=skill_id,
            model_id=model_id,
            status="running",
            steps=[],
            output_text="",
            total_elapsed_ms=0,
            created_at=datetime.now().isoformat(),
        )
        self._active_runs[rid] = record
        self._start_times[rid] = time.perf_counter()
        if self.store:
            try:
                self.store.save_run(record)
            except Exception:
                pass
        return record

    def record_step(
        self,
        run_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any = None,
        permission_level: int = 0,
        status: str = "success",
        elapsed_ms: int = 0,
        error: Optional[str] = None,
    ) -> ToolCallStep:
        run = self._active_runs.get(run_id)
        step_index = len(run.steps) if run else 0
        step = ToolCallStep(
            step_index=step_index,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            permission_level=permission_level,
            status=status,
            elapsed_ms=elapsed_ms,
            error=error,
        )
        if run:
            run.steps.append(step)
            if self.store:
                try:
                    self.store.save_run(run)
                except Exception:
                    pass
        return step

    def finish_run(
        self,
        run_id: str,
        status: str = "completed",
        output_text: str = "",
    ) -> Optional[RunRecord]:
        run = self._active_runs.get(run_id)
        start_t = self._start_times.pop(run_id, None)
        total_ms = int((time.perf_counter() - start_t) * 1000) if start_t else 0

        if not run:
            if self.store:
                run = self.store.get_run(run_id)
            if not run:
                return None

        run.status = status
        run.output_text = output_text
        run.total_elapsed_ms = total_ms
        if self.store:
            try:
                self.store.save_run(run)
            except Exception:
                pass
        return run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        if run_id in self._active_runs:
            return self._active_runs[run_id]
        if self.store:
            return self.store.get_run(run_id)
        return None

    def list_runs(self, project_id: Optional[str] = None, limit: int = 50) -> List[RunRecord]:
        if self.store:
            return self.store.list_runs(project_id=project_id, limit=limit)
        return list(self._active_runs.values())[:limit]
