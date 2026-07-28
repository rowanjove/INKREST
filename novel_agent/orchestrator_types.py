"""Shared types for novel orchestration (avoids circular imports)."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ChapterResult:
    chapter_id: str
    final_path: Path
    audit: Dict[str, Any]
    warnings: List[str] = dataclasses.field(default_factory=list)