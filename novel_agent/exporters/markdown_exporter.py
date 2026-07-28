"""Markdown publication exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from novel_agent.domain.publishing import PublicationBook
from novel_agent.exporters.chapter_export import chapter_heading, collect_publication_book


def render_markdown(book: PublicationBook) -> str:
    if not book.chapters:
        raise ValueError("No chapters found to export")
    parts = [f"# {book.title}"]
    for chapter in book.chapters:
        body = chapter.markdown_text or chapter.plain_text
        parts.append(f"## {chapter_heading(chapter)}\n\n{body}")
    return "\n\n".join(parts) + "\n"


def export_markdown(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    title: str = "未命名小说",
) -> Path:
    book = collect_publication_book(
        root_dir,
        title=title,
        chapter_ids=chapter_ids,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(book), encoding="utf-8")
    return output
