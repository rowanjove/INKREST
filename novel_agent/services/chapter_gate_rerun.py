"""Re-run unified_gate only (no planner/generation)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from novel_agent.phases.base import ChapterContext
from novel_agent.progress import emit_progress

if TYPE_CHECKING:
    from novel_agent.orchestrator import ChapterResult, NovelOrchestrator


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_context_for_gate(orchestrator: "NovelOrchestrator", chapter_id: str) -> ChapterContext:
    chapter_dir = orchestrator.root_dir / "workspace" / "chapters" / f"chapter_{chapter_id}"
    if not chapter_dir.is_dir():
        raise FileNotFoundError(f"Chapter {chapter_id} not found")
    reports_dir = chapter_dir / "reports"
    final_text = _read_text(chapter_dir / "chapter_final.txt")
    if not final_text:
        raise ValueError("本章尚无正文，无法只重跑门禁")
    plan = _read_json(chapter_dir / "plan.json")
    goal = (
        plan.get("chapter_goal")
        or plan.get("detailed_synopsis")
        or plan.get("chapter_title")
        or f"Gate rerun {chapter_id}"
    )
    return ChapterContext(
        chapter_id=chapter_id,
        chapter_goal=str(goal),
        chapter_dir=chapter_dir,
        scenes_dir=chapter_dir / "scenes",
        reports_dir=reports_dir,
        plan=plan,
        final_text=final_text,
        audit=_read_json(reports_dir / "audit.json"),
        chapter_summary=_read_text(chapter_dir / "chapter_summary.md"),
        wordcount=_read_json(reports_dir / "wordcount.json"),
        extracted_state=_read_json(chapter_dir / "state_update.json"),
        warnings=(),
    )


async def run_gate_only_rerun(
    orchestrator: "NovelOrchestrator",
    chapter_id: str,
) -> "ChapterResult":
    from novel_agent.orchestrator import ChapterResult
    from novel_agent.services.unified_gate import run_unified_review_gate

    ctx = load_context_for_gate(orchestrator, chapter_id)
    chapter_dir = ctx.chapter_dir
    reports_dir = ctx.reports_dir

    emit_progress("unified_gate", "running", chapter_id=chapter_id)
    gate = await run_unified_review_gate(
        orchestrator, chapter_id, ctx, reports_dir, chapter_dir
    )
    ctx = gate.ctx

    if gate.blocked:
        orchestrator._rollback_checkpoint_stages(
            chapter_dir,
            chapter_id,
            list(
                orchestrator._load_checkpoint(chapter_dir).get("completed_stages") or []
            ),
            drop_stages=("audit", "post_audit"),
            last_stage="quality_blocked",
            progress_step="unified_gate",
            progress_status="blocked",
            progress_data={
                "resumable_from": "audit",
                "mode": gate.quality_report.get("mode"),
                "gate_only_rerun": True,
            },
            checkpoint_extra={},
        )
        return ChapterResult(
            chapter_id=chapter_id,
            final_path=chapter_dir / "chapter_final.txt",
            audit=ctx.audit or {},
            warnings=list(ctx.warnings) + [gate.block_message],
        )

    checkpoint_path = chapter_dir / "checkpoint.json"
    if checkpoint_path.is_file():
        try:
            cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            cp["resolved_at"] = datetime.now().isoformat()
            cp["last_stage"] = "unified_gate"
            completed: List[str] = list(cp.get("completed_stages") or [])
            if "unified_gate" not in completed and "audit" in completed:
                completed.append("unified_gate")
            cp["completed_stages"] = completed
            checkpoint_path.write_text(
                json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except (json.JSONDecodeError, OSError):
            pass

    try:
        from novel_agent.services.batch_retry_queue import dismiss_batch_retry

        dismiss_batch_retry(orchestrator.root_dir, chapter_id)
    except Exception:
        pass

    emit_progress("unified_gate", "done", chapter_id=chapter_id)
    return ChapterResult(
        chapter_id=chapter_id,
        final_path=chapter_dir / "chapter_final.txt",
        audit=ctx.audit or {},
        warnings=list(ctx.warnings),
    )