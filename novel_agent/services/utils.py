import logging
from typing import Any, Dict, List, Optional
from novel_agent.control.calibration import build_calibration_report
from novel_agent.control.narrative_debt import classify_debt
from novel_agent.orchestrator_checkpoint import ChapterCheckpoint
from novel_agent.agents.asset_compressor import compress_assets

logger = logging.getLogger("novel_agent.services.utils")

_COMPRESS_EVENT_THRESHOLD = 100

def auto_compress_assets(orchestrator: Any, threshold: Optional[int] = None) -> None:
    try:
        from novel_agent.control.long_run import resolve_compress_schedule

        if threshold is None:
            _, _, threshold = resolve_compress_schedule(orchestrator.root_dir)
        state = orchestrator.state_manager.get_state()
        event_count = len(state.get("events", []))
        if event_count < (threshold or _COMPRESS_EVENT_THRESHOLD):
            return
        compress_assets(orchestrator.root_dir, orchestrator.config.get_llm("asset_compressor"), orchestrator.prompts)
    except Exception as exc:
        logger.warning("Auto asset compression failed: %s", exc)

def write_calibration_report(
    orchestrator: Any,
    chapter_id: str,
    planned_chapters: Optional[List[Dict[str, Any]]] = None,
) -> None:
    try:
        outline_path = orchestrator.root_dir / "workspace" / "outline.json"
        outline = ChapterCheckpoint.load_data(outline_path)
        chapters = planned_chapters or orchestrator.store.get_chapters()
        debt = {
            "foreshadows": classify_debt(orchestrator.store.list_foreshadows(), chapter_id, default_period=10),
            "reader_promises": classify_debt(orchestrator.store.list_reader_promises(), chapter_id, default_period=3),
            "secrets": classify_debt(orchestrator.store.list_secrets(), chapter_id, default_period=15),
        }
        report = build_calibration_report(outline, chapters, debt)
        orchestrator._write_json(
            orchestrator.root_dir / "workspace" / "reports" / f"calibration_chapter_{chapter_id}.json",
            report,
        )
    except Exception as exc:
        logger.warning("Calibration report failed for chapter %s: %s", chapter_id, exc)
