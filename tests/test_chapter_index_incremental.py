"""Incremental chapter index sync skips unchanged folders."""

from pathlib import Path

from novel_agent.services.chapter_index_sync import (
    chapter_dir_signature,
    sync_chapters_from_disk,
)
from novel_agent.state.sqlite_store import SQLiteStateStore


def _write_chapter(root: Path, chapter_id: str, *, text: str = "正文") -> Path:
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter_final.txt").write_text(text, encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        f'{{"chapter_title": "Ch{chapter_id}"}}',
        encoding="utf-8",
    )
    return chapter_dir


def test_incremental_sync_skips_unchanged(tmp_path: Path) -> None:
    _write_chapter(tmp_path, "001")
    store = SQLiteStateStore(tmp_path)

    first = sync_chapters_from_disk(tmp_path, store)
    second = sync_chapters_from_disk(tmp_path, store)

    assert first == 1
    assert second == 0
    assert store.count_chapters_indexed() == 1


def test_incremental_sync_reindexes_on_mtime_change(tmp_path: Path) -> None:
    chapter_dir = _write_chapter(tmp_path, "002", text="第一版")
    store = SQLiteStateStore(tmp_path)
    assert sync_chapters_from_disk(tmp_path, store) == 1

    before_sig = chapter_dir_signature(chapter_dir)
    (chapter_dir / "chapter_final.txt").write_text("第二版更长正文", encoding="utf-8")
    after_sig = chapter_dir_signature(chapter_dir)
    assert after_sig != before_sig

    assert sync_chapters_from_disk(tmp_path, store) == 1