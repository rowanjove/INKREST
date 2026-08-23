"""Cross-chapter expression memory and repetition diagnostics."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.quality.expression_memory import (
    build_expression_memory_index,
    check_expression_repetition,
    extract_expression_entries,
    load_expression_memory,
    load_expression_memory_rules,
    refresh_expression_memory,
    save_expression_memory_rules,
)
from novel_agent.quality.report import build_quality_report


class TestExpressionMemory(unittest.TestCase):
    def test_extracts_categorised_source_anchored_entries(self):
        text = "然而他抬起眼。她的手指轻轻敲着桌面，像雨点落下。门在下一刻打开。"
        entries = extract_expression_entries(text, chapter_id="003")

        kinds = {entry["kind"] for entry in entries}
        self.assertIn("sentence_opening", kinds)
        self.assertIn("body_reaction", kinds)
        self.assertIn("imagery", kinds)
        self.assertIn("transition", kinds)
        self.assertIn("ending_hook", kinds)
        self.assertTrue(all(entry["start"] < entry["end"] for entry in entries))
        self.assertTrue(all(entry["chapter_id"] == "003" for entry in entries))

    def test_cross_chapter_reuse_is_report_only_and_has_evidence(self):
        with tempfile.TemporaryDirectory(prefix="expression-memory-") as raw_root:
            root = Path(raw_root)
            documents = [
                {
                    "chapter_id": "001",
                    "text": "她的手指轻轻敲着桌面。雨声压住了屋里的沉默。",
                },
                {
                    "chapter_id": "002",
                    "text": "她的手指轻轻敲着桌面。门外有人停下。",
                },
            ]
            index = build_expression_memory_index(documents)
            result = check_expression_repetition(
                documents[1]["text"],
                root,
                chapter_id="002",
                index=index,
            )

            self.assertTrue(result["pass"])
            self.assertFalse(result["blocking"])
            self.assertTrue(any(item["kind"] == "body_reaction" for item in result["findings"]))
            finding = next(item for item in result["findings"] if item["kind"] == "body_reaction")
            self.assertEqual(finding["chapter_ids"], ["001"])
            self.assertEqual(finding["action"], "review")
            self.assertTrue(finding["evidence"])
            self.assertGreaterEqual(len(result["clusters"]), 1)

    def test_refresh_persists_authoritative_chapter_index(self):
        with tempfile.TemporaryDirectory(prefix="expression-memory-refresh-") as raw_root:
            root = Path(raw_root)
            chapter = root / "workspace" / "chapters" / "chapter_001"
            chapter.mkdir(parents=True)
            (chapter / "chapter_final.txt").write_text("她的手指轻轻敲着桌面。", encoding="utf-8")

            index = refresh_expression_memory(root)
            loaded = load_expression_memory(root)

            self.assertEqual(index["source_count"], 1)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["source_count"], 1)
            self.assertTrue((root / "workspace" / "reports" / "expression_memory.json").is_file())

    def test_quality_report_exposes_repetition_check_without_blocking(self):
        with tempfile.TemporaryDirectory(prefix="expression-memory-report-") as raw_root:
            root = Path(raw_root)
            chapter = root / "workspace" / "chapters" / "chapter_001"
            chapter.mkdir(parents=True)
            (chapter / "chapter_final.txt").write_text("她的手指轻轻敲着桌面。", encoding="utf-8")
            chapter_2 = root / "workspace" / "chapters" / "chapter_002"
            chapter_2.mkdir(parents=True)
            text = "她的手指轻轻敲着桌面。门外有人停下。"
            (chapter_2 / "chapter_final.txt").write_text(text, encoding="utf-8")

            report = build_quality_report(text, root_dir=root, chapter_id="002")

            check = report["checks"]["expression_repetition"]
            self.assertTrue(check["pass"])
            self.assertFalse(check["blocking"])
            self.assertGreaterEqual(len(check["findings"]), 1)
            persisted = json.loads(
                (root / "workspace" / "reports" / "expression_memory.json").read_text(encoding="utf-8")
            )
            self.assertEqual(persisted["schema_version"], 1)

    def test_context_builder_receives_bounded_avoidance_block(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        with tempfile.TemporaryDirectory(prefix="expression-memory-context-") as raw_root:
            root = Path(raw_root)
            chapter = root / "workspace" / "chapters" / "chapter_001"
            chapter.mkdir(parents=True)
            (chapter / "chapter_final.txt").write_text("她的手指轻轻敲着桌面。", encoding="utf-8")
            refresh_expression_memory(root)

            builder = ContextBuilderAgent(root)
            block = builder._build_expression_avoidance_block({"chapter_id": "002"})

            self.assertIn("[EXPRESSION_CONTRACT]", block)
            self.assertIn("近期已采用的表达", block)
            self.assertIn("避免复读", block)
            self.assertIn("第001章", block)

    def test_local_rules_allow_whitelist_and_functional_recurrence(self):
        with tempfile.TemporaryDirectory(prefix="expression-memory-rules-") as raw_root:
            root = Path(raw_root)
            documents = [
                {"chapter_id": "001", "text": "她的手指轻轻敲着桌面。"},
                {"chapter_id": "002", "text": "她的手指轻轻敲着桌面。"},
            ]
            index = build_expression_memory_index(documents)
            body_entry = next(item for item in index["entries"] if item["kind"] == "body_reaction")
            save_expression_memory_rules(
                root,
                {
                    "allowlist": [{"kind": "body_reaction", "normalized": body_entry["normalized"]}],
                    "functional_recurrence": [{"kind": "sentence_opening", "text": "她的手指"}],
                },
            )
            self.assertEqual(len(load_expression_memory_rules(root)["allowlist"]), 1)

            result = check_expression_repetition(
                documents[1]["text"],
                root,
                chapter_id="002",
                index=index,
            )

            self.assertEqual(result["allowlist_count"], 1)
            self.assertFalse(any(item["kind"] == "body_reaction" for item in result["findings"]))

    def test_functional_recurrence_is_keep_evidence_and_not_avoidance_prompt(self):
        with tempfile.TemporaryDirectory(prefix="expression-memory-functional-") as raw_root:
            root = Path(raw_root)
            documents = [
                {"chapter_id": "001", "text": "然而他抬起眼。"},
                {"chapter_id": "002", "text": "然而他抬起眼。门外有人停下。"},
            ]
            index = build_expression_memory_index(documents)
            transition = next(item for item in index["entries"] if item["kind"] == "transition")
            functional_rules = [
                {"kind": item["kind"], "fingerprint": item["fingerprint"]}
                for item in index["entries"]
                if item["kind"] in {"sentence_opening", "transition", "ending_hook"}
            ]
            save_expression_memory_rules(
                root,
                {"functional_recurrence": functional_rules},
            )

            result = check_expression_repetition(
                documents[1]["text"],
                root,
                chapter_id="002",
                index=index,
            )
            finding = next(item for item in result["findings"] if item["kind"] == "transition")
            self.assertTrue(finding["functional_recurrence"])
            self.assertEqual(finding["action"], "keep")
            self.assertEqual(result["score"], 100)

            # The same functional recurrence must not be injected as an
            # avoidance instruction for the next writer.
            from novel_agent.quality.expression_memory import build_expression_avoidance_context

            block = build_expression_avoidance_context(root, "003")
            self.assertNotIn("然而他抬起眼", block)


if __name__ == "__main__":
    unittest.main()
