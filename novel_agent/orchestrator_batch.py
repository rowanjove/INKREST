"""Helpers for multi-chapter / arc batch orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from novel_agent.logging_config import get_logger
from novel_agent.orchestrator_checkpoint import ChapterCheckpoint
from novel_agent.progress import emit_progress

logger = get_logger("orchestrator.batch")


def record_batch_retry_skip(
    root_dir: Path,
    chapter_id: str,
    arc_id: str,
    *,
    reason: str,
    message: str,
    step: str,
) -> None:
    try:
        from novel_agent.services.batch_retry_queue import record_batch_retry

        record_batch_retry(
            root_dir,
            chapter_id=chapter_id,
            arc_id=arc_id,
            reason=reason,
            step=step,
            message=message,
        )
    except Exception as exc:
        logger.warning("Failed to record batch retry for %s: %s", chapter_id, exc)


def maybe_pause_after_skip(
    root_dir: Path,
    chapter_id: str,
    arc_id: str,
    consecutive_skips: int,
    skip_pause_max: int,
) -> bool:
    if skip_pause_max <= 0 or consecutive_skips < skip_pause_max:
        return False
    from novel_agent.services.arc_queue import record_novel_batch_paused

    record_novel_batch_paused(
        root_dir,
        reason="batch_skip_limit",
        last_chapter=chapter_id,
        arc_id=arc_id,
        streak=consecutive_skips,
    )
    emit_progress(
        "novel_batch",
        "paused",
        {
            "reason": "batch_skip_limit",
            "streak": consecutive_skips,
            "last_chapter": chapter_id,
            "arc_id": arc_id,
        },
        chapter_id,
    )
    return True


def chapter_pipeline_complete(root_dir: Path, chapter_id: str) -> bool:
    chapter_dir = root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    checkpoint = ChapterCheckpoint().load(chapter_dir)
    completed = checkpoint.get("completed_stages") or []
    return "post_audit" in completed