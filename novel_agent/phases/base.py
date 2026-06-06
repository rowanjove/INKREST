from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class ChapterContext:
    chapter_id: str
    chapter_goal: str
    chapter_dir: Path
    scenes_dir: Path
    reports_dir: Path
    
    # 流水线各步骤所产生/更新的数据
    plan: Optional[Dict[str, Any]] = None
    final_text: Optional[str] = None
    audit: Optional[Dict[str, Any]] = None
    chapter_summary: Optional[str] = None
    wordcount: Optional[Dict[str, Any]] = None
    extracted_state: Optional[Dict[str, Any]] = None
    warnings: Tuple[str, ...] = ()


class PipelinePhase:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.config = orchestrator.config
        self.logger = orchestrator.logger if hasattr(orchestrator, "logger") else None
