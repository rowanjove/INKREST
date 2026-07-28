"""Dependency-free EPUB 3 publication exporter."""

from __future__ import annotations

import re
import uuid
import zipfile
from html import escape
from pathlib import Path
from typing import Iterable, Optional

from novel_agent.domain.publishing import PublicationBook, PublicationChapter
from novel_agent.exporters.chapter_export import chapter_heading, collect_publication_book
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.epub")


def _chapter_slug(chapter: PublicationChapter, index: int) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", chapter.chapter_id).strip("-")
    return safe or f"{index:04d}"


def _chapter_xhtml(chapter: PublicationChapter) -> str:
    paragraphs = "\n".join(
        f"    <p>{escape(line.strip())}</p>"
        for line in chapter.plain_text.splitlines()
        if line.strip()
    )
    heading = escape(chapter_heading(chapter))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN" lang="zh-CN">
  <head><meta charset="utf-8"/><title>{heading}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
  <body>
    <h1>{heading}</h1>
{paragraphs}
  </body>
</html>
"""


def _nav_xhtml(book: PublicationBook, entries: list[tuple[str, str]]) -> str:
    items = "\n".join(
        f'        <li><a href="{filename}">{escape(label)}</a></li>'
        for filename, label in entries
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">
  <head><meta charset="utf-8"/><title>{escape(book.title)}目录</title></head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>目录</h1>
      <ol>
{items}
      </ol>
    </nav>
  </body>
</html>
"""


def _package_opf(book: PublicationBook, entries: list[tuple[str, str]]) -> str:
    identifier = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"inkrest:{book.title}:{'|'.join(ch.chapter_id for ch in book.chapters)}",
    )
    manifest = "\n".join(
        f'    <item id="chapter-{slug}" href="{filename}" media-type="application/xhtml+xml"/>'
        for (filename, slug) in entries
    )
    spine = "\n".join(
        f'    <itemref idref="chapter-{slug}"/>'
        for (_filename, slug) in entries
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="zh-CN">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:{identifier}</dc:identifier>
    <dc:title>{escape(book.title)}</dc:title>
    <dc:language>{escape(book.language)}</dc:language>
    <dc:creator>{escape(book.author)}</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="style" href="style.css" media-type="text/css"/>
{manifest}
  </manifest>
  <spine>
{spine}
  </spine>
</package>
"""


def export_epub(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    title: str = "未命名小说",
    author: str = "栖墨",
) -> Path:
    book = collect_publication_book(
        root_dir,
        title=title,
        author=author,
        chapter_ids=chapter_ids,
    )
    if not book.chapters:
        raise ValueError("No chapters found to export")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, str]] = []
    for index, chapter in enumerate(book.chapters, start=1):
        slug = _chapter_slug(chapter, index)
        entries.append((f"chapter-{slug}.xhtml", slug))

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="utf-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""",
        )
        archive.writestr("EPUB/package.opf", _package_opf(book, entries))
        archive.writestr(
            "EPUB/nav.xhtml",
            _nav_xhtml(
                book,
                [
                    (filename, chapter_heading(chapter))
                    for (filename, _slug), chapter in zip(entries, book.chapters)
                ],
            ),
        )
        archive.writestr(
            "EPUB/style.css",
            "body{font-family:serif;line-height:1.8;margin:5%;}"
            "h1{text-align:center;margin:2em 0;}p{text-indent:2em;margin:.6em 0;}",
        )
        for (filename, _slug), chapter in zip(entries, book.chapters):
            archive.writestr(f"EPUB/{filename}", _chapter_xhtml(chapter))

    logger.info("Exported %d chapters to %s", len(book.chapters), output)
    return output
