"""Markdown publication exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, TextIO

from novel_agent.exporters.chapter_export import chapter_heading, iter_publication_chapters


def _write_markdown_stream(
    handle: TextIO,
    root_dir: Path,
    *,
    title: str,
    chapter_ids: Optional[Iterable[str]] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    handle.write(f"# {title}\n")
    count = 0
    for chapter in iter_publication_chapters(root_dir, chapter_ids=chapter_ids):
        body = chapter.markdown_text or chapter.plain_text
        handle.write(f"\n## {chapter_heading(chapter)}\n\n{body}\n")
        count += 1
        if progress_callback:
            progress_callback(count)
    return count


def export_markdown(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    title: str = "未命名小说",
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            count = _write_markdown_stream(
                handle,
                root_dir,
                title=str(title or "未命名小说"),
                chapter_ids=chapter_ids,
                progress_callback=progress_callback,
            )
        if count <= 0:
            raise ValueError("No chapters found to export")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output
