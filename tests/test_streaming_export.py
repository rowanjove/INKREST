"""TXT/Markdown export iterates SQLite documents instead of materializing the book."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from novel_agent.exporters.markdown_exporter import export_markdown
from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.services.longform_synth import seed_synthetic_project


def test_txt_export_does_not_build_full_publication_book(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=8, seed=2)
    output = tmp_path / "out" / "book.txt"
    with patch(
        "novel_agent.exporters.chapter_export.collect_publication_book",
        side_effect=AssertionError("TXT must stream, not collect the full book"),
    ):
        result = export_txt(tmp_path, output)
    text = result.read_text(encoding="utf-8")
    assert "第 1 章" in text
    assert "第 8 章" in text
    assert "第1章正文" in text
    assert not output.with_name(output.name + ".tmp").exists()


def test_markdown_export_is_atomic_and_ordered(tmp_path: Path) -> None:
    seed_synthetic_project(tmp_path, chapters=5, seed=4)
    output = tmp_path / "book.md"
    with patch(
        "novel_agent.exporters.chapter_export.collect_publication_book",
        side_effect=AssertionError("Markdown must stream, not collect the full book"),
    ):
        export_markdown(tmp_path, output, title="流式书")
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# 流式书")
    assert text.index("第 1 章") < text.index("第 5 章")
    assert not list(output.parent.glob("*.tmp"))


def test_txt_export_failure_does_not_leave_success_file(tmp_path: Path) -> None:
    output = tmp_path / "empty.txt"
    try:
        export_txt(tmp_path, output)
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert not output.exists()
