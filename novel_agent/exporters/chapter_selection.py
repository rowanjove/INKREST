"""Shared chapter selection helpers for exporters."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Set


def normalize_chapter_id(chapter_id: str) -> str:
    value = str(chapter_id or "").strip()
    if value.isdigit():
        return f"{int(value):03d}"
    return value


def selected_chapter_ids(chapter_ids: Optional[Iterable[str]]) -> Set[str]:
    return {
        normalized
        for raw in (chapter_ids or [])
        if (normalized := normalize_chapter_id(str(raw)))
    }


def filter_chapter_dirs(
    chapter_dirs: Iterable[Path],
    chapter_ids: Optional[Iterable[str]],
) -> list[Path]:
    selected = selected_chapter_ids(chapter_ids)
    if not selected:
        return list(chapter_dirs)
    return [
        chapter_dir
        for chapter_dir in chapter_dirs
        if normalize_chapter_id(chapter_dir.name.replace("chapter_", "", 1)) in selected
    ]
