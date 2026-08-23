"""SQLite persistence for source-aware NarrativeEvent projections."""

import tempfile
import unittest
from pathlib import Path

from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection


class TestNarrativeEventStore(unittest.TestCase):
    def test_upsert_keeps_prior_revision_as_superseded(self):
        with tempfile.TemporaryDirectory(prefix="narrative-event-store-") as raw_root:
            root = Path(raw_root)
            store = SQLiteStateStore(root)

            first = store.upsert_narrative_events(
                "001",
                [
                    {
                        "id": "E001",
                        "summary": "林澈拿到钥匙。",
                        "characters": ["林澈"],
                        "objects": ["钥匙"],
                        "threads": ["地下室"],
                    }
                ],
                source_document_id="chapter:001",
                source_revision_id="rev-1",
            )
            second = store.upsert_narrative_events(
                "001",
                [
                    {
                        "id": "E001",
                        "summary": "林澈把钥匙交给沈砚。",
                        "characters": ["林澈", "沈砚"],
                        "objects": ["钥匙"],
                        "threads": ["地下室"],
                        "outcome": "沈砚暂时保管。",
                    }
                ],
                source_document_id="chapter:001",
                source_revision_id="rev-2",
            )

            current = store.list_narrative_events(chapter_id="001")
            history = store.list_narrative_events(chapter_id="001", include_superseded=True)

            self.assertEqual(first, ["E001@rev-1"])
            self.assertEqual(second, ["E001@rev-2"])
            self.assertEqual(len(current), 1)
            self.assertEqual(current[0]["projection_id"], "E001@rev-2")
            self.assertEqual(current[0]["outcome"], "沈砚暂时保管。")
            self.assertEqual(len(history), 2)
            old = next(item for item in history if item["projection_id"] == "E001@rev-1")
            self.assertEqual(old["superseded_by"], "E001@rev-2")

            by_actor = store.list_narrative_events(actor="沈砚")
            self.assertEqual(len(by_actor), 1)
            by_thread = store.list_narrative_events(thread="地下室")
            self.assertEqual(len(by_thread), 1)

            with safe_connection(store.db_path) as conn:
                row = conn.execute(
                    "select source_document_id, source_revision_id from narrative_events where projection_id = ?",
                    ("E001@rev-2",),
                ).fetchone()
            self.assertEqual(row[0], "chapter:001")
            self.assertEqual(row[1], "rev-2")

    def test_dual_story_time_and_knowledge_scope_round_trip(self):
        with tempfile.TemporaryDirectory(prefix="narrative-event-time-") as raw_root:
            store = SQLiteStateStore(Path(raw_root))
            store.upsert_narrative_events(
                "003",
                [
                    {
                        "id": "E-TIME",
                        "summary": "密室真相",
                        "story_time_start": "冬至",
                        "story_time_end": "冬至夜",
                        "truth_scope": "character_belief",
                        "knower_ids": ["林澈"],
                        "invalidated_at_revision": "rev-4",
                    }
                ],
                source_revision_id="rev-3",
            )
            event = store.list_narrative_events(chapter_id="003")[0]
            self.assertEqual(event["story_time_start"], "冬至")
            self.assertEqual(event["story_time_end"], "冬至夜")
            self.assertEqual(event["truth_scope"], "character_belief")
            self.assertEqual(event["knower_ids"], ["林澈"])
            self.assertEqual(event["invalidated_at_revision"], "rev-4")

    def test_clear_narrative_state_includes_event_projection_table(self):
        with tempfile.TemporaryDirectory(prefix="narrative-event-clear-") as raw_root:
            root = Path(raw_root)
            store = SQLiteStateStore(root)
            store.upsert_narrative_events("001", [{"id": "E001", "summary": "事件"}])

            cleared = store.clear_narrative_state()

            self.assertIn("narrative_events", cleared)
            self.assertEqual(store.list_narrative_events(), [])

    def test_delete_chapter_removes_event_projection(self):
        with tempfile.TemporaryDirectory(prefix="narrative-event-delete-") as raw_root:
            root = Path(raw_root)
            store = SQLiteStateStore(root)
            store.upsert_narrative_events("001", [{"id": "E001", "summary": "事件"}])
            store.index_chapter("001", "第一章", root / "chapter.txt", 1, "")

            store.delete_chapter_index("001")

            self.assertEqual(store.list_narrative_events(), [])

    def test_context_builder_recalls_only_prior_source_events(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        with tempfile.TemporaryDirectory(prefix="narrative-event-context-") as raw_root:
            root = Path(raw_root)
            store = SQLiteStateStore(root)
            store.upsert_narrative_events(
                "002",
                [{"id": "E002", "summary": "林澈拿到钥匙。", "characters": ["林澈"]}],
            )
            store.upsert_narrative_events(
                "004",
                [{"id": "E004", "summary": "林澈打开门。", "characters": ["林澈"]}],
            )

            builder = ContextBuilderAgent(root)
            block = builder._build_event_evidence_block(
                {"chapter_id": "003", "characters": ["林澈"]}
            )

            self.assertIn("E002", block)
            self.assertNotIn("E004", block)
            self.assertIn("[硬事实]", block)

    def test_context_builder_fuses_four_event_evidence_routes(self):
        from novel_agent.agents.context_builder import ContextBuilderAgent

        class FakeVector:
            def search(self, *args, **kwargs):
                return [
                    {
                        "id": "E_SEM",
                        "text": "语义召回的同一把钥匙曾出现在地下室。",
                        "metadata": {"chapter": "001"},
                    }
                ]

        with tempfile.TemporaryDirectory(prefix="narrative-event-four-routes-") as raw_root:
            root = Path(raw_root)
            store = SQLiteStateStore(root)
            store.upsert_narrative_events(
                "002",
                [{"id": "E_ADJ", "summary": "林澈保管铜钥匙。", "characters": ["林澈"], "objects": ["铜钥匙"]}],
            )
            store.sync_state_update(
                "001",
                {
                    "foreshadows": [
                        {
                            "id": "F_OPEN",
                            "title": "地下室的门",
                            "description": "钥匙仍未插入锁孔。",
                            "status": "open",
                            "related_characters": ["林澈"],
                        }
                    ]
                },
            )
            builder = ContextBuilderAgent(root, vector_store=FakeVector())
            block = builder._build_event_evidence_block(
                {
                    "chapter_id": "003",
                    "purpose": "寻找铜钥匙",
                    "characters": ["林澈"],
                    "objects": ["铜钥匙"],
                }
            )

            self.assertIn("[邻近事件]", block)
            self.assertIn("[实体关联]", block)
            self.assertIn("[语义事件]", block)
            self.assertIn("[开放线程]", block)


if __name__ == "__main__":
    unittest.main()
