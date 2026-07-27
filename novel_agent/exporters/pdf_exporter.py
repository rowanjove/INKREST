"""Chinese-safe PDF publication exporter using ReportLab."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable, Optional

from novel_agent.exporters.chapter_export import chapter_heading, collect_publication_book
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.pdf")


def export_pdf(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[Iterable[str]] = None,
    title: str = "未命名小说",
) -> Path:
    try:
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF export; install the production requirements"
        ) from exc

    book = collect_publication_book(
        root_dir,
        title=title,
        chapter_ids=chapter_ids,
    )
    if not book.chapters:
        raise ValueError("No chapters found to export")

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.4 * cm,
        rightMargin=2.4 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title=book.title,
        author=book.author,
    )
    title_style = ParagraphStyle(
        "PublicationTitle",
        fontName="STSong-Light",
        fontSize=24,
        leading=34,
        alignment=TA_CENTER,
        spaceAfter=32,
    )
    chapter_style = ParagraphStyle(
        "PublicationChapter",
        fontName="STSong-Light",
        fontSize=18,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=22,
    )
    body_style = ParagraphStyle(
        "PublicationBody",
        fontName="STSong-Light",
        fontSize=11.5,
        leading=21,
        firstLineIndent=23,
        spaceAfter=7,
    )
    story: list[object] = [
        Paragraph(escape(book.title), title_style),
        Spacer(1, 42),
        PageBreak(),
    ]
    for index, chapter in enumerate(book.chapters):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(escape(chapter_heading(chapter)), chapter_style))
        for line in chapter.plain_text.splitlines():
            if line.strip():
                story.append(Paragraph(escape(line.strip()), body_style))
    document.build(story)
    logger.info("Exported %d chapters to %s", len(book.chapters), output)
    return output
