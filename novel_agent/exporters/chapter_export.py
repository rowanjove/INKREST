"""Authoritative manuscript collection shared by all publication exporters."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

from novel_agent.domain.publishing import PublicationBook, PublicationChapter
from novel_agent.exporters.chapter_selection import selected_chapter_ids
from novel_agent.state.sqlite_store import SQLiteStateStore

# Kept as an import-compatible name for first-party extensions.
ExportChapter = PublicationChapter


def _matches_selection(chapter_id: str, selected: set[str]) -> bool:
    if not selected:
        return True
    normalized = (
        f"{int(chapter_id):03d}" if str(chapter_id).isdigit() else str(chapter_id)
    )
    return normalized in selected


def iter_publication_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> Iterator[PublicationChapter]:
    """Yield publication chapters from SQLite without materializing the full book."""
    store = SQLiteStateStore(Path(root_dir))
    selected = selected_chapter_ids(chapter_ids)
    selected_list = list(selected) if selected else None
    for row in store.iter_manuscript_export_rows(chapter_ids=selected_list):
        chapter_id = str(row["chapter_id"])
        if not _matches_selection(chapter_id, selected):
            continue
        yield PublicationChapter(
            chapter_id=chapter_id,
            title=str(row["title"]).strip(),
            plain_text=str(row["plain_text"]),
            markdown_text=str(row["markdown_text"]),
            revision=int(row["revision"]),
            word_count=int(row["word_count"] or len(str(row["plain_text"]))),
        )


def collect_publication_book(
    root_dir: Path,
    *,
    title: str = "未命名小说",
    author: str = "栖墨",
    chapter_ids: Optional[Iterable[str]] = None,
) -> PublicationBook:
    """Build a publication snapshot from SQLite, never from disk projections."""
    chapters = list(iter_publication_chapters(root_dir, chapter_ids=chapter_ids))
    return PublicationBook(
        title=str(title or "未命名小说").strip() or "未命名小说",
        author=str(author or "栖墨").strip() or "栖墨",
        chapters=chapters,
    )


def iter_export_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> Iterator[ExportChapter]:
    yield from iter_publication_chapters(root_dir, chapter_ids=chapter_ids)


def collect_export_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> list[ExportChapter]:
    return list(iter_export_chapters(root_dir, chapter_ids))


def chapter_heading(chapter: PublicationChapter) -> str:
    number = (
        str(int(chapter.chapter_id))
        if chapter.chapter_id.isdigit()
        else chapter.chapter_id
    )
    heading = f"第 {number} 章"
    return f"{heading}　{chapter.title}" if chapter.title else heading
