"""Exporters for generating novel output files."""

from pathlib import Path
from typing import Any, List, Optional

from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.exporters.epub_exporter import export_epub
from novel_agent.exporters.pdf_exporter import export_pdf
from novel_agent.exporters.markdown_exporter import export_markdown
from novel_agent.exporters.docx_exporter import export_docx

__all__ = [
    "export_txt",
    "export_epub",
    "export_pdf",
    "export_markdown",
    "export_docx",
    "export_novel",
]


def export_novel(
    root_dir: Path,
    output_path: Path,
    format: str,
    title: str = "未命名小说",
    chapter_ids: Optional[List[str]] = None,
    plugin_manager: Optional[Any] = None,
    **kwargs
) -> Path:
    """Unified entry point to export novels using builtin or plugin exporters."""
    format_lower = format.lower()

    if plugin_manager:
        exporters = plugin_manager.get_exporters()
        if format_lower in exporters:
            return exporters[format_lower].export(
                root_dir=Path(root_dir),
                output_path=Path(output_path),
                chapter_ids=chapter_ids,
                title=title,
                **kwargs
            )

    if format_lower == "txt":
        export_txt(root_dir, output_path, chapter_ids=chapter_ids)
        return output_path
    elif format_lower == "epub":
        export_epub(root_dir, output_path, chapter_ids=chapter_ids, title=title)
        return output_path
    elif format_lower == "pdf":
        export_pdf(root_dir, output_path, chapter_ids=chapter_ids, title=title)
        return output_path
    elif format_lower in {"markdown", "md"}:
        export_markdown(root_dir, output_path, chapter_ids=chapter_ids, title=title)
        return output_path
    elif format_lower == "docx":
        export_docx(root_dir, output_path, chapter_ids=chapter_ids, title=title)
        return output_path

    raise ValueError(f"Unsupported export format: {format}")
