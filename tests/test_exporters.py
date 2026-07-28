from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from novel_agent.exporters.chapter_export import collect_export_chapters
from novel_agent.exporters.epub_exporter import export_epub
from novel_agent.exporters.docx_exporter import export_docx
from novel_agent.exporters.markdown_exporter import export_markdown
from novel_agent.exporters.pdf_exporter import export_pdf
from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.services.manuscript_documents import plain_text_to_tiptap
from novel_agent.state.sqlite_store import SQLiteStateStore


class ExportersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="novel-agent-exporters-")
        self.root = Path(self.tempdir.name)
        self.store = SQLiteStateStore(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _create_document(
        self,
        chapter_id: str,
        title: str,
        text: str,
        *,
        disk_text: str = "",
    ) -> None:
        content = plain_text_to_tiptap(text)
        self.store.create_manuscript_document(
            chapter_id=chapter_id,
            title=title,
            content_json=content,
            plain_text=text,
            markdown_text=text,
            source="test",
        )
        self.store.index_chapter(
            chapter_id,
            title,
            self.root
            / "workspace"
            / "chapters"
            / f"chapter_{chapter_id}"
            / "chapter_final.txt",
            len(text),
            "",
            has_final=bool(text),
            gate_status="passed" if text else "",
        )
        if disk_text:
            chapter_dir = (
                self.root / "workspace" / "chapters" / f"chapter_{chapter_id}"
            )
            chapter_dir.mkdir(parents=True, exist_ok=True)
            (chapter_dir / "chapter_final.txt").write_text(
                disk_text,
                encoding="utf-8",
            )

    def test_collection_uses_sqlite_documents_not_disk_projection(self) -> None:
        self._create_document(
            "001",
            "雨夜",
            "数据库中的正文。",
            disk_text="不应被导出的旧文件正文。",
        )

        chapters = collect_export_chapters(self.root)

        self.assertEqual([chapter.chapter_id for chapter in chapters], ["001"])
        self.assertEqual(chapters[0].title, "雨夜")
        self.assertEqual(chapters[0].text, "数据库中的正文。")

    def test_collection_orders_numerically_and_matches_ids_exactly(self) -> None:
        for chapter_id in ("011", "001", "002"):
            self._create_document(chapter_id, f"标题 {chapter_id}", chapter_id)

        chapters = collect_export_chapters(self.root, ["11", "1"])

        self.assertEqual([chapter.chapter_id for chapter in chapters], ["001", "011"])

    def test_export_txt_uses_normalized_book_and_can_hide_headers(self) -> None:
        self._create_document("001", "雨夜", "林越听到雨声。")
        self._create_document("002", "惊雷", "天空闪过一道白光。")
        output = self.root / "book.txt"

        export_txt(self.root, output, include_title=True)

        text = output.read_text(encoding="utf-8")
        self.assertIn("第 1 章　雨夜", text)
        self.assertIn("第 2 章　惊雷", text)
        self.assertIn("林越听到雨声。", text)

        export_txt(self.root, output, include_title=False, chapter_ids=["2"])
        self.assertEqual(output.read_text(encoding="utf-8"), "天空闪过一道白光。")

    def test_exporters_reject_empty_selection(self) -> None:
        self._create_document("001", "雨夜", "正文")
        with self.assertRaisesRegex(ValueError, "No chapters"):
            export_txt(self.root, self.root / "empty.txt", chapter_ids=["999"])
        with self.assertRaisesRegex(ValueError, "No chapters"):
            export_epub(self.root, self.root / "empty.epub", chapter_ids=["999"])

    def test_epub_is_self_contained_epub3_and_escapes_content(self) -> None:
        self._create_document("001", "雨夜 <开始>", "林越 & 风雨\n门外 <无人>。")
        output = self.root / "book.epub"

        export_epub(self.root, output, title="测试 & 书名", author="作者")

        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist()[0], "mimetype")
            self.assertEqual(
                archive.read("mimetype"),
                b"application/epub+zip",
            )
            container = archive.read("META-INF/container.xml").decode("utf-8")
            package = archive.read("EPUB/package.opf").decode("utf-8")
            navigation = archive.read("EPUB/nav.xhtml").decode("utf-8")
            chapter = archive.read("EPUB/chapter-001.xhtml").decode("utf-8")

        self.assertIn('full-path="EPUB/package.opf"', container)
        self.assertIn('version="3.0"', package)
        self.assertIn('properties="nav"', package)
        self.assertIn('idref="chapter-001"', package)
        self.assertIn("雨夜 &lt;开始&gt;", navigation)
        self.assertIn("林越 &amp; 风雨", chapter)
        self.assertIn("门外 &lt;无人&gt;。", chapter)

    def test_markdown_and_docx_use_the_same_publication_snapshot(self) -> None:
        import docx

        self._create_document(
            "001",
            "雨夜",
            "数据库正文。",
            disk_text="旧文件正文。",
        )
        markdown = self.root / "book.md"
        document = self.root / "book.docx"

        export_markdown(self.root, markdown, title="测试书名")
        export_docx(self.root, document, title="测试书名")

        markdown_text = markdown.read_text(encoding="utf-8")
        docx_text = "\n".join(
            paragraph.text for paragraph in docx.Document(document).paragraphs
        )
        self.assertIn("# 测试书名", markdown_text)
        self.assertIn("数据库正文。", markdown_text)
        self.assertNotIn("旧文件正文。", markdown_text)
        self.assertIn("测试书名", docx_text)
        self.assertIn("数据库正文。", docx_text)
        self.assertNotIn("旧文件正文。", docx_text)

    def test_pdf_requires_reportlab_with_actionable_error(self) -> None:
        self._create_document("001", "雨夜", "正文")
        real_import = __import__

        def blocked_import(name, *args, **kwargs):
            if name.startswith("reportlab"):
                raise ModuleNotFoundError("reportlab unavailable")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocked_import):
            with self.assertRaisesRegex(ImportError, "reportlab is required"):
                export_pdf(self.root, self.root / "book.pdf")

    def test_pdf_generates_when_reportlab_is_available(self) -> None:
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab is not installed in the current test environment")
        self._create_document("001", "雨夜", "林越听到雨声。")
        output = self.root / "book.pdf"

        export_pdf(self.root, output, title="测试书名")

        self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
        self.assertGreater(output.stat().st_size, 1_000)


if __name__ == "__main__":
    unittest.main()
