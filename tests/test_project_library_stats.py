"""SQLite-backed project library stats."""

from pathlib import Path

from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.services.project_library_stats import project_library_stats
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_project_library_stats_from_index(tmp_path: Path) -> None:
    chapters = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapters.mkdir(parents=True)
    (chapters / "chapter_final.txt").write_text("一二三四五", encoding="utf-8")
    sync_chapters_from_disk(tmp_path, SQLiteStateStore(tmp_path))

    count, words = project_library_stats(tmp_path)

    assert count == 1
    assert words >= 5