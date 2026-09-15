"""Disk sync must not purge SQLite manuscript when chapter folders are missing."""

from pathlib import Path

from novel_agent.services.chapter_index_sync import sync_chapters_from_disk
from novel_agent.services.manuscript_workspace import ensure_manuscript_document
from novel_agent.state.sqlite_store import SQLiteStateStore


def _write_chapter(root: Path, chapter_id: str, text: str = "权威正文") -> None:
    chapter_dir = root / "workspace" / "chapters" / f"chapter_{chapter_id}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter_final.txt").write_text(text, encoding="utf-8")
    (chapter_dir / "plan.json").write_text(
        f'{{"chapter_title": "Ch{chapter_id}"}}',
        encoding="utf-8",
    )


def test_sync_keeps_sqlite_manuscript_when_disk_folder_missing(tmp_path: Path) -> None:
    _write_chapter(tmp_path, "007", "不可删除的成稿")
    store = SQLiteStateStore(tmp_path)
    ensure_manuscript_document(tmp_path, "007", store=store)
    assert store.get_manuscript_document("007")["plain_text"].strip() == "不可删除的成稿"

    import shutil

    shutil.rmtree(tmp_path / "workspace" / "chapters" / "chapter_007")

    sync_chapters_from_disk(tmp_path, store)

    document = store.get_manuscript_document("007")
    assert document is not None
    assert document["plain_text"].strip() == "不可删除的成稿"
    assert store.get_manuscript_document_summary("007") is not None


def test_sync_drops_only_empty_index_rows_without_documents(tmp_path: Path) -> None:
    _write_chapter(tmp_path, "008")
    store = SQLiteStateStore(tmp_path)
    assert sync_chapters_from_disk(tmp_path, store) == 1
    store.index_chapter(
        "ghost",
        "幽灵章",
        tmp_path / "workspace" / "chapters" / "chapter_ghost" / "chapter_final.txt",
        0,
        "",
    )
    sync_chapters_from_disk(tmp_path, store)
    ids = {row["id"] for row in store.get_chapters()}
    assert "008" in ids
    assert "ghost" not in ids
