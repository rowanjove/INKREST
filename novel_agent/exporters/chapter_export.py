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


def collect_publication_book(
    root_dir: Path,
    *,
    title: str = "未命名小说",
    author: str = "栖墨",
    chapter_ids: Optional[Iterable[str]] = None,
) -> PublicationBook:
    """Build a publication snapshot from SQLite, never from disk projections."""
    store = SQLiteStateStore(Path(root_dir))
    selected = selected_chapter_ids(chapter_ids)
    chapters: list[PublicationChapter] = []
    for document in store.list_manuscript_documents():
        chapter_id = str(document["chapter_id"])
        if not _matches_selection(chapter_id, selected):
            continue
        plain_text = str(document["plain_text"]).strip()
        if not plain_text:
            continue
        chapters.append(
            PublicationChapter(
                chapter_id=chapter_id,
                title=str(document["title"]).strip(),
                plain_text=plain_text,
                markdown_text=str(document["markdown_text"]).strip(),
                revision=int(document["revision"]),
                word_count=len(plain_text),
            )
        )
    return PublicationBook(
        title=str(title or "未命名小说").strip() or "未命名小说",
        author=str(author or "栖墨").strip() or "栖墨",
        chapters=chapters,
    )


def iter_export_chapters(
    root_dir: Path,
    chapter_ids: Optional[Iterable[str]] = None,
) -> Iterator[ExportChapter]:
    yield from collect_publication_book(
        root_dir,
        chapter_ids=chapter_ids,
    ).chapters


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
