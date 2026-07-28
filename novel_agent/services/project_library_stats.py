"""Lightweight chapter/word stats for project library cards."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.services.progress_summary import load_progress_snapshot_stats
from novel_agent.state.sqlite_store import SQLiteStateStore


def project_library_stats(project_dir: Path) -> Tuple[int, int]:
    """Return (chapter_count, total_words) using SQLite index with snapshot fallback."""
    store = SQLiteStateStore(project_dir)
    if store.count_chapters_indexed() == 0:
        chapters_dir = project_dir / "workspace" / "chapters"
        if chapters_dir.is_dir() and any(chapters_dir.glob("chapter_*")):
            sync_chapters_from_disk(project_dir, store)
    count = store.count_chapters_indexed()
    words = store.sum_chapters_word_count_indexed() if count else 0
    if count:
        return count, words

    snapshot = load_progress_snapshot_stats(project_dir)
    if snapshot:
        return (
            int(snapshot.get("library_indexed") or 0),
            int(snapshot.get("total_words") or 0),
        )
    return 0, 0