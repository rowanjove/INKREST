"""Evidence-oriented narrative event projection tests."""

import tempfile
import unittest
from pathlib import Path

from novel_agent.quality.event_memory import (
    build_event_evidence_context,
    build_narrative_event_projection,
    load_narrative_event_projections,
    normalise_narrative_event,
    write_narrative_event_projection,
)


class TestEventMemory(unittest.TestCase):
    def test_normalises_legacy_event_without_guessing_missing_fields(self):
        event = normalise_narrative_event(
            {
                "id": "E_001",
                "summary": "林澈拿到钥匙。",
                "characters": ["林澈"],
                "objects": ["钥匙"],
                "threads": ["地下室"],
            },
            chapter_id="001",
            source_document_id="chapter:001",
            source_revision_id="rev-1",
        )

        self.assertEqual(event["id"], "E_001")
        self.assertEqual(event["actors"], ["林澈"])
        self.assertEqual(event["objects"], ["钥匙"])
        self.assertEqual(event["action"], "林澈拿到钥匙。")
        self.assertEqual(event["outcome"], "")
        self.assertEqual(event["source_document_id"], "chapter:001")
        self.assertEqual(event["source_revision_id"], "rev-1")
        self.assertEqual(event["confidence"], 0.0)

    def test_projection_round_trip_and_evidence_context(self):
        with tempfile.TemporaryDirectory(prefix="event-memory-") as raw_root:
            root = Path(raw_root)
            events = [
                {
                    "id": "E_002",
                    "summary": "沈砚打开信封。",
                    "outcome": "他只看见半页内容。",
                    "characters": ["沈砚"],
                    "objects": ["信封"],
                    "threads": ["秘密"],
                    "confidence": 0.82,
                }
            ]
            projection = build_narrative_event_projection(
                "002",
                events,
                source_document_id="chapter:002",
                source_revision_id="rev-3",
            )
            self.assertEqual(projection["event_count"], 1)
            path = write_narrative_event_projection(
                root,
                "002",
                events,
                source_document_id="chapter:002",
                source_revision_id="rev-3",
            )
            loaded = load_narrative_event_projections(root)
            context = build_event_evidence_context(loaded, actor="沈砚", object_name="信封")

            self.assertTrue(path.is_file())
            self.assertEqual(len(loaded), 1)
            self.assertEqual(len(context), 1)
            self.assertIn("[硬事实][event:E_002][第002章]", context[0]["text"])
            self.assertIn("结果：他只看见半页内容。", context[0]["text"])
            self.assertEqual(context[0]["source_revision_id"], "rev-3")

    def test_context_filters_by_thread_and_limits_newest_first(self):
        events = [
            {"id": "E1", "chapter_id": "001", "action": "旧线索", "threads": ["A"]},
            {"id": "E2", "chapter_id": "010", "action": "新线索", "threads": ["A"]},
            {"id": "E3", "chapter_id": "011", "action": "无关", "threads": ["B"]},
        ]
        context = build_event_evidence_context(events, thread="A", limit=1)

        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["event_id"], "E2")


if __name__ == "__main__":
    unittest.main()
