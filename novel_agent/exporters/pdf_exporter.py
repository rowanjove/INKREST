"""PDF exporter using reportlab."""

import json
from pathlib import Path
from typing import List, Optional

from novel_agent.exporters.chapter_selection import filter_chapter_dirs
from novel_agent.logging_config import get_logger

logger = get_logger("exporters.pdf")


def export_pdf(
    root_dir: Path,
    output_path: Path,
    chapter_ids: Optional[List[str]] = None,
    title: str = "未命名小说",
) -> Path:
    """Export chapters as a PDF file.

    Requires: pip install reportlab

    Args:
        root_dir: Project root directory.
        output_path: Where to write the .pdf file.
        chapter_ids: Specific chapter IDs to export. None = all chapters.
        title: Book title.

    Returns:
        Path to the generated file.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            PageBreak,
        )
    except ImportError:
        raise ImportError("reportlab is required for PDF export: pip install reportlab")

    # Try to register a Chinese font
    font_name = "Helvetica"
    for font_path in [
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                font_name = "ChineseFont"
                break
            except Exception:
                continue

    chapters_dir = root_dir / "workspace" / "chapters"
    if not chapters_dir.exists():
        raise FileNotFoundError(f"Chapters directory not found: {chapters_dir}")

    chapter_dirs = filter_chapter_dirs(sorted(chapters_dir.glob("chapter_*")), chapter_ids)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BookTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=24,
        spaceAfter=30,
    )
    chapter_style = ParagraphStyle(
        "ChapterTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=18,
        spaceBefore=20,
        spaceAfter=16,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=12,
        leading=20,
        spaceAfter=8,
    )

    story: list = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 40))

    chapter_count = 0
    for ch_dir in chapter_dirs:
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

        if chapter_count > 0:
            story.append(PageBreak())

        story.append(Paragraph(chapter_title, chapter_style))
        story.append(Spacer(1, 12))

        for para in text.split("\n"):
            para = para.strip()
            if para:
                # Escape XML special characters
                safe = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe, body_style))

        chapter_count += 1

    if chapter_count == 0:
        raise ValueError("No chapters found to export")

    doc.build(story)
    logger.info("Exported %d chapters to %s", chapter_count, output_path)
    return output_path
