"""Shared chapter iteration for markdown/docx exporters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from novel_agent.exporters.chapter_selection import filter_chapter_dirs


@dataclass(frozen=True)
class ExportChapter:
    chapter_id: str
    title: str
    text: str


def _chapter_title(plan_path: Path) -> str:
    if not plan_path.is_file():
        return ""
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(plan.get("chapter_title") or "").strip()


def _format_chapter_number(chapter_id: str) -> str:
    return str(int(chapter_id)) if chapter_id.isdigit() else chapter_id


def iter_export_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> Iterator[ExportChapter]:
    chapters_dir = root_dir / "workspace" / "chapters"
    if not chapters_dir.is_dir():
        raise FileNotFoundError("Chapters directory not found")

    chapter_dirs = filter_chapter_dirs(
        sorted(chapters_dir.glob("chapter_*")),
        chapter_ids,
    )
    for ch_dir in chapter_dirs:
        final_path = ch_dir / "chapter_final.txt"
        if not final_path.is_file():
            continue
        text = final_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        chapter_id = ch_dir.name.replace("chapter_", "", 1)
        yield ExportChapter(
            chapter_id=chapter_id,
            title=_chapter_title(ch_dir / "plan.json"),
            text=text,
        )


def collect_export_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> List[ExportChapter]:
    return list(iter_export_chapters(root_dir, chapter_ids))