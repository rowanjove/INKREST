"""Plain-text publication exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, TextIO

from novel_agent.exporters.chapter_export import chapter_heading, iter_publication_chapters
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.txt")


def _write_txt_stream(
    handle: TextIO,
    root_dir: Path,
    *,
    chapter_ids: Optional[Iterable[str]] = None,
    include_title: bool = True,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    count = 0
    for chapter in iter_publication_chapters(root_dir, chapter_ids=chapter_ids):
        if count:
            handle.write("\n\n\n")
        if include_title:
            handle.write(
                f"{'=' * 40}\n{chapter_heading(chapter)}\n{'=' * 40}\n\n{chapter.plain_text}"
            )
        else:
            handle.write(chapter.plain_text)
        count += 1
        if progress_callback:
            progress_callback(count)
    return count


def export_txt(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    include_title: bool = True,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            count = _write_txt_stream(
                handle,
                root_dir,
                chapter_ids=chapter_ids,
                include_title=include_title,
                progress_callback=progress_callback,
            )
        if count <= 0:
            raise ValueError("No chapters found to export")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    logger.info("Exported %d chapters to %s", count, output)
    return output
