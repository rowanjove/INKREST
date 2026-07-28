"""Chapter checkpoint persistence for the novel pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from novel_agent.logging_config import get_logger
from novel_agent.progress import emit_progress

logger = get_logger("orchestrator.checkpoint")

WriteJsonFn = Callable[[Path, Dict[str, Any]], None]


class ChapterCheckpoint:
    """Load/save/rollback chapter_{id}/checkpoint.json."""

    def load(self, chapter_dir: Path) -> Dict[str, Any]:
        path = chapter_dir / "checkpoint.json"
        if not path.exists():
            return {"completed_stages": [], "chapter_id": ""}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"completed_stages": [], "chapter_id": ""}

    def save(
        self,
        chapter_dir: Path,
        chapter_id: str,
        stage: str,
        completed: List[str],
        write_json: WriteJsonFn,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        data: Dict[str, Any] = {
            "chapter_id": chapter_id,
            "completed_stages": completed,
            "last_stage": stage,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            data.update(extra)
        write_json(chapter_dir / "checkpoint.json", data)

    def rollback_stages(
        self,
        chapter_dir: Path,
        chapter_id: str,
        completed: List[str],
        drop_stages: Tuple[str, ...],
        last_stage: str,
        progress_step: str,
        progress_status: str,
        write_json: WriteJsonFn,
        progress_data: Optional[Dict[str, Any]] = None,
        checkpoint_extra: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        rolled = [stage for stage in completed if stage not in drop_stages]
        if rolled != completed:
            logger.info(
                "Chapter %s checkpoint rolled back (%s) from %s to %s",
                chapter_id,
                last_stage,
                completed,
                rolled,
            )
        extra: Dict[str, Any] = {}
        if progress_data and progress_data.get("resumable_from"):
            extra["resumable_from"] = progress_data["resumable_from"]
        if checkpoint_extra:
            extra.update(checkpoint_extra)
        self.save(
            chapter_dir,
            chapter_id,
            last_stage,
            rolled,
            write_json,
            extra=extra or None,
        )
        emit_progress(
            progress_step,
            progress_status,
            progress_data or {},
            chapter_id,
        )
        return rolled

    def rollback_after_approval_rejection(
        self,
        chapter_dir: Path,
        chapter_id: str,
        completed: List[str],
        write_json: WriteJsonFn,
    ) -> List[str]:
        return self.rollback_stages(
            chapter_dir,
            chapter_id,
            completed,
            drop_stages=("audit", "post_audit"),
            last_stage="approval_rejected",
            progress_step="approval",
            progress_status="rejected",
            write_json=write_json,
            progress_data={"resumable_from": "audit"},
        )

    @staticmethod
    def load_data(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}