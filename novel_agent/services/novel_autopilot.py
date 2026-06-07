"""Multi-round novel continue: drain arc queue toward target with progress reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from novel_agent.logging_config import get_logger
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import load_pipeline_settings
from novel_agent.progress import emit_progress
from novel_agent.services.arc_queue import load_arc_progress

logger = get_logger("services.novel_autopilot")


def _append_autopilot_round_log(root_dir: Path, summary: Dict[str, Any]) -> None:
    """Append per-round summary for assistant / agent snapshot consumers."""
    try:
        from datetime import datetime

        path = root_dir / "workspace" / "autopilot_rounds.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {**summary, "ts": datetime.now().isoformat()}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Failed to append autopilot round log: %s", exc)


@dataclass
class AutopilotResult:
    rounds: int = 0
    chapters_completed: int = 0
    stopped_reason: str = ""
    paused: bool = False
    round_summaries: List[Dict[str, Any]] = field(default_factory=list)


def resolve_autopilot_settings(root_dir: Path) -> Dict[str, int]:
    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    per_round = int(runtime.get("autopilot_chapters_per_round") or 10)
    max_rounds = int(runtime.get("autopilot_max_rounds") or 300)
    return {
        "chapters_per_round": max(1, min(per_round, 100)),
        "max_rounds": max(1, min(max_rounds, 2000)),
    }


def _load_outline_target(root_dir: Path) -> int:
    for rel in ("workspace/outline.json", "outline.json"):
        path = root_dir / rel
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            prof = data.get("scale_profile") or {}
            target = int(
                data.get("target_chapters")
                or prof.get("target_chapters")
                or prof.get("max_chapters")
                or 0
            )
            if target > 0:
                return target
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    return 0


def chapters_remaining_to_target(root_dir: Path) -> int:
    """How many more chapters may be generated before outline target."""
    target = _load_outline_target(root_dir)
    if target <= 0 or target >= 999999:
        return 0
    try:
        from novel_agent.state.sqlite_store import SQLiteStateStore

        done = SQLiteStateStore(root_dir).count_chapters()
    except Exception:
        progress = load_arc_progress(root_dir)
        done = int(progress.get("completed_chapters") or 0)
    return max(0, target - done)


def is_batch_circuit_paused(root_dir: Path) -> bool:
    progress = load_arc_progress(root_dir)
    return (
        progress.get("status") == "paused"
        and str(progress.get("pause_reason") or "") == "circuit_breaker"
    )


def has_more_batch_work(root_dir: Path, complete_fn) -> bool:
    from novel_agent.services.rolling_planner import count_pending_briefs as _count_pending

    if _count_pending(root_dir, complete_fn) > 0:
        return True
    remaining = chapters_remaining_to_target(root_dir)
    return remaining > 0


async def run_novel_autopilot(
    orchestrator: Any,
    *,
    max_chapters: int = 0,
    chapters_per_round: int = 0,
    full_book: bool = True,
    max_rounds: int = 0,
) -> AutopilotResult:
    """
    Repeatedly run arc/novel continue until target, idle, circuit pause, or caps.

    max_chapters: total cap across all rounds (0 = until idle/target).
    chapters_per_round: per-round cap (0 = use settings default).
    """
    root = orchestrator.root_dir
    settings = resolve_autopilot_settings(root)
    per_round = chapters_per_round or settings["chapters_per_round"]
    rounds_limit = max_rounds or settings["max_rounds"]
    complete_fn = orchestrator._chapter_pipeline_complete
    from novel_agent.services.rolling_planner import count_pending_briefs

    outcome = AutopilotResult()
    total_cap = int(max_chapters) if max_chapters and max_chapters > 0 else 0
    stuck_rounds = 0
    last_pending_snapshot = -1

    emit_progress(
        "novel_autopilot",
        "running",
        {
            "round": 0,
            "chapters_completed": 0,
            "per_round": per_round,
            "full_book": full_book,
        },
    )

    for round_idx in range(1, rounds_limit + 1):
        if is_batch_circuit_paused(root):
            outcome.stopped_reason = "circuit_breaker"
            outcome.paused = True
            break

        if total_cap and outcome.chapters_completed >= total_cap:
            outcome.stopped_reason = "chapter_cap"
            break

        remaining_target = chapters_remaining_to_target(root)
        if remaining_target == 0 and not has_more_batch_work(root, complete_fn):
            outcome.stopped_reason = "target_reached"
            break

        round_cap: Optional[int] = per_round
        if total_cap:
            left = total_cap - outcome.chapters_completed
            round_cap = min(per_round, left) if left > 0 else 0
        if remaining_target > 0 and round_cap:
            round_cap = min(round_cap, remaining_target)

        if round_cap is not None and round_cap <= 0:
            outcome.stopped_reason = "chapter_cap"
            break

        logger.info(
            "Autopilot round %d/%d (cap=%s, full_book=%s)",
            round_idx,
            rounds_limit,
            round_cap,
            full_book,
        )

        if isinstance(orchestrator, NovelOrchestrator):
            orchestrator.reset_round_token_accumulator()

        if full_book:
            batch = await orchestrator.arun_arcs(
                resume=True,
                max_chapters=round_cap,
            )
        else:
            batch = await orchestrator.arun_novel_continue(
                resume=True,
                max_chapters=round_cap,
            )

        n = len(batch)
        tokens_used = 0
        if isinstance(orchestrator, NovelOrchestrator):
            tokens_used = orchestrator.consume_round_tokens()
        outcome.rounds = round_idx
        outcome.chapters_completed += n
        summary = {
            "round": round_idx,
            "chapters": n,
            "last_id": str(getattr(batch[-1], "chapter_id", "") or "") if batch else "",
            "tokens_used": tokens_used,
            "stopped_reason": "",
        }
        outcome.round_summaries.append(summary)
        _append_autopilot_round_log(root, summary)

        emit_progress(
            "novel_autopilot",
            "running",
            {
                "round": round_idx,
                "chapters_completed": outcome.chapters_completed,
                "last_chapter": str(getattr(batch[-1], "chapter_id", "") or "") if batch else "",
            },
        )

        if is_batch_circuit_paused(root):
            outcome.stopped_reason = "circuit_breaker"
            outcome.paused = True
            break

        if n == 0 and not has_more_batch_work(root, complete_fn):
            outcome.stopped_reason = "idle"
            break

        pending_now = count_pending_briefs(root, complete_fn)
        if n == 0 and pending_now > 0:
            if pending_now == last_pending_snapshot:
                stuck_rounds += 1
            else:
                stuck_rounds = 0
                last_pending_snapshot = pending_now
            if stuck_rounds >= 3:
                outcome.stopped_reason = "stuck_chapter"
                emit_progress(
                    "novel_autopilot",
                    "paused",
                    {
                        "reason": "stuck_chapter",
                        "pending_briefs": pending_now,
                        "message": "多轮未推进待写章节，已暂停以免重复烧 token",
                    },
                )
                outcome.paused = True
                break
        else:
            stuck_rounds = 0
            last_pending_snapshot = pending_now if pending_now >= 0 else last_pending_snapshot

        if remaining_target > 0:
            remaining_target = chapters_remaining_to_target(root)
            if remaining_target == 0 and not has_more_batch_work(root, complete_fn):
                outcome.stopped_reason = "target_reached"
                break
    else:
        if not outcome.stopped_reason:
            outcome.stopped_reason = "max_rounds"

    status = "paused" if outcome.paused else "done"
    emit_progress(
        "novel_autopilot",
        status,
        {
            "rounds": outcome.rounds,
            "chapters_completed": outcome.chapters_completed,
            "stopped_reason": outcome.stopped_reason,
        },
    )
    return outcome