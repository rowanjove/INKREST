"""EPUB exporter using ebooklib."""

import json
from html import escape as html_escape
from pathlib import Path
from typing import List, Optional

from novel_agent.exporters.chapter_selection import filter_chapter_dirs
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.epub")


def export_epub(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[List[str]] = None,
    title: str = "未命名小说",
    author: str = "NovelAgent",
) -> Path:
    """Export chapters as an EPUB file.

    Requires: pip install ebooklib

    Args:
        root_dir: Project root directory.
        output_path: Where to write the .epub file.
        chapter_ids: Specific chapter IDs to export. None = all chapters.
        title: Book title.
        author: Book author.

    Returns:
        Path to the generated file.
    """
    try:
        from ebooklib import epub
    except ImportError:
        raise ImportError("ebooklib is required for EPUB export: pip install ebooklib")

    chapters_dir = root_dir / "workspace" / "chapters"
    if not chapters_dir.exists():
        raise FileNotFoundError(f"Chapters directory not found: {chapters_dir}")

    chapter_dirs = filter_chapter_dirs(sorted(chapters_dir.glob("chapter_*")), chapter_ids)

    book = epub.EpubBook()
    book.set_identifier("novel-agent-export")
    book.set_title(title)
    book.set_language("zh")
    book.add_author(author)

    epub_chapters: list = []
    toc: list = []
    spine = ["nav"]

    for idx, ch_dir in enumerate(chapter_dirs):
        final_path = ch_dir / "chapter_final.txt"
        if not final_path.exists():
            logger.warning("Skipping %s: no chapter_final.txt", ch_dir.name)
            continue

        text = final_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        chapter_id = ch_dir.name.replace("chapter_", "")
        chapter_title = f"第 {chapter_id} 章"

        plan_path = ch_dir / "plan.json"
        if plan_path.exists():
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                if plan.get("chapter_title"):
                    chapter_title += f"  {plan['chapter_title']}"
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load chapter plan from %s: %s", plan_path, exc)

        paragraphs = text.split("\n")
        html_content = "\n".join(
            f"<p>{html_escape(p.strip())}</p>" for p in paragraphs if p.strip()
        )

        ch = epub.EpubHtml(
            title=chapter_title,
            file_name=f"chapter_{chapter_id}.xhtml",
            lang="zh",
        )
        ch.content = f"<h1>{html_escape(chapter_title)}</h1>\n{html_content}"
        book.add_item(ch)
        epub_chapters.append(ch)
        toc.append(ch)
        spine.append(ch)

    if not epub_chapters:
        raise ValueError("No chapters found to export")

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    logger.info("Exported %d chapters to %s", len(epub_chapters), output_path)
    return output_path
