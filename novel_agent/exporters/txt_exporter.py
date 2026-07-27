"""Plain-text publication exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from novel_agent.domain.publishing import PublicationBook
from novel_agent.exporters.chapter_export import chapter_heading, collect_publication_book
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.txt")


def render_txt(book: PublicationBook, *, include_title: bool = True) -> str:
    if not book.chapters:
        raise ValueError("No chapters found to export")
    if not include_title:
        return "\n\n\n".join(chapter.plain_text for chapter in book.chapters)
    parts = [
        f"{'=' * 40}\n{chapter_heading(chapter)}\n{'=' * 40}\n\n{chapter.plain_text}"
        for chapter in book.chapters
    ]
    return "\n\n\n".join(parts)


def export_txt(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    include_title: bool = True,
) -> Path:
    book = collect_publication_book(root_dir, chapter_ids=chapter_ids)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_txt(book, include_title=include_title), encoding="utf-8")
    logger.info("Exported %d chapters to %s", len(book.chapters), output)
    return output
