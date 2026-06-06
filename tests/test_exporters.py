import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.exporters.epub_exporter import export_epub
from novel_agent.exporters.pdf_exporter import export_pdf


class ExportersTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-exporters-test-"))
        # Setup dummy chapter workspace
        self.chapters_dir = self.tmpdir / "workspace" / "chapters"
        self.chapters_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_dummy_chapter(self, cid: str, title: str, content: str):
        ch_dir = self.chapters_dir / f"chapter_{cid}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        (ch_dir / "chapter_final.txt").write_text(content, encoding="utf-8")
        plan = {"chapter_title": title, "chapter_id": cid}
        (ch_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    # -----------------------------------------------------------------------
    # TXT Exporter Tests
    # -----------------------------------------------------------------------

    def test_export_txt_raises_file_not_found(self):
        empty_dir = self.tmpdir / "empty"
        empty_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            export_txt(empty_dir, self.tmpdir / "out.txt")

    def test_export_txt_success_with_title(self):
        self._create_dummy_chapter("001", "雨夜", "林澈听到雨声。")
        self._create_dummy_chapter("002", "惊雷", "天空闪过一道白光。")
        
        out_path = self.tmpdir / "output.txt"
        export_txt(self.tmpdir, out_path, include_title=True)
        
        self.assertTrue(out_path.exists())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("第 001 章  雨夜", content)
        self.assertIn("林澈听到雨声。", content)
        self.assertIn("第 002 章  惊雷", content)
        self.assertIn("天空闪过一道白光。", content)

    def test_export_txt_success_without_title(self):
        self._create_dummy_chapter("001", "雨夜", "林澈听到雨声。")
        out_path = self.tmpdir / "output.txt"
        export_txt(self.tmpdir, out_path, include_title=False)
        
        content = out_path.read_text(encoding="utf-8")
        self.assertNotIn("第 001 章", content)
        self.assertEqual(content.strip(), "林澈听到雨声。")

    def test_export_txt_skips_empty_or_missing_chapter_final(self):
        # Chapter 001 is missing final
        ch1 = self.chapters_dir / "chapter_001"
        ch1.mkdir(parents=True)
        (ch1 / "plan.json").write_text(json.dumps({"chapter_title": "A"}), encoding="utf-8")
        
        # Chapter 002 has empty final
        self._create_dummy_chapter("002", "B", "")
        
        # Chapter 003 is valid
        self._create_dummy_chapter("003", "C", "林澈看到信件。")
        
        out_path = self.tmpdir / "output.txt"
        export_txt(self.tmpdir, out_path)
        
        content = out_path.read_text(encoding="utf-8")
        self.assertNotIn("第 001 章", content)
        self.assertNotIn("第 002 章", content)
        self.assertIn("第 003 章", content)
        self.assertIn("林澈看到信件。", content)

    def test_export_txt_invalid_json_handling(self):
        ch1 = self.chapters_dir / "chapter_001"
        ch1.mkdir(parents=True)
        (ch1 / "chapter_final.txt").write_text("雨一直在下。", encoding="utf-8")
        # Write corrupted json
        (ch1 / "plan.json").write_text("{corrupt json", encoding="utf-8")
        
        out_path = self.tmpdir / "output.txt"
        # Should complete without raising JSONDecodeError
        export_txt(self.tmpdir, out_path, include_title=True)
        
        self.assertTrue(out_path.exists())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("第 001 章", content)
        self.assertIn("雨一直在下。", content)

    # -----------------------------------------------------------------------
    # EPUB Exporter Tests
    # -----------------------------------------------------------------------

    def test_export_epub_raises_import_error_when_ebooklib_missing(self):
        # We patchsys.modules to simulate ebooklib not installed
        with patch.dict(sys.modules, {"ebooklib": None}):
            with self.assertRaises(ImportError) as ctx:
                export_epub(self.tmpdir, self.tmpdir / "out.epub")
            self.assertIn("ebooklib is required", str(ctx.exception))

    def test_export_epub_success_if_installed(self):
        try:
            import ebooklib
        except ImportError:
            self.skipTest("ebooklib not installed, skipping real EPUB export test")
            
        self._create_dummy_chapter("001", "雨夜", "林澈听到雨声。")
        self._create_dummy_chapter("002", "惊雷", "天空闪过\n一道白光。")
        
        out_path = self.tmpdir / "output.epub"
        export_epub(self.tmpdir, out_path, title="测试书名", author="测试作者")
        
        self.assertTrue(out_path.exists())

    def test_export_epub_raises_value_error_if_no_chapters(self):
        try:
            import ebooklib
        except ImportError:
            self.skipTest("ebooklib not installed, skipping real EPUB validation test")
            
        out_path = self.tmpdir / "output.epub"
        with self.assertRaises(ValueError):
            export_epub(self.tmpdir, out_path)

    # -----------------------------------------------------------------------
    # PDF Exporter Tests
    # -----------------------------------------------------------------------

    def test_export_pdf_raises_import_error_when_reportlab_missing(self):
        with patch.dict(sys.modules, {"reportlab": None, "reportlab.lib.pagesizes": None}):
            with self.assertRaises(ImportError) as ctx:
                export_pdf(self.tmpdir, self.tmpdir / "out.pdf")
            self.assertIn("reportlab is required", str(ctx.exception))

    def test_export_pdf_success_if_installed(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("reportlab not installed, skipping real PDF export test")
            
        self._create_dummy_chapter("001", "雨夜", "林澈听到雨声。")
        self._create_dummy_chapter("002", "惊雷", "天空闪过\n一道白光。")
        
        out_path = self.tmpdir / "output.pdf"
        export_pdf(self.tmpdir, out_path, title="测试书名")
        
        self.assertTrue(out_path.exists())

    def test_export_pdf_raises_value_error_if_no_chapters(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("reportlab not installed, skipping real PDF validation test")
            
        out_path = self.tmpdir / "output.pdf"
        with self.assertRaises(ValueError):
            export_pdf(self.tmpdir, out_path)


if __name__ == "__main__":
    unittest.main()
