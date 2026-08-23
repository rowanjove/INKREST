"""Source-aware state conflict diagnostics."""

import json
import tempfile
import unittest
from pathlib import Path

from novel_agent.quality.event_consistency import check_event_consistency
from novel_agent.quality.report import build_quality_report
from novel_agent.state.sqlite_store import SQLiteStateStore


class TestEventConsistency(unittest.TestCase):
    def _store(self, root: Path) -> SQLiteStateStore:
        store = SQLiteStateStore(root)
        store.sync_state_update(
            "001",
            {
                "characters": {
                    "林澈": {"name": "林澈", "location": "旧城区", "physical_state": "左臂受伤"},
                    "沈砚": {"name": "沈砚", "location": "旧城区"},
                },
                "objects": [{"id": "key-1", "name": "铜钥匙", "holder": "林澈"}],
                "secrets": [
                    {
                        "id": "secret-1",
                        "title": "父亲身份",
                        "description": "父亲是卧底",
                        "status": "hidden",
                    }
                ],
                "events": [
                    {
                        "id": "E001",
                        "summary": "林澈在旧城区保管铜钥匙。",
                        "characters": ["林澈"],
                        "objects": ["铜钥匙"],
                        "location": "旧城区",
                    }
                ],
            },
        )
        store.upsert_narrative_events(
            "001",
            [
                {
                    "id": "E001",
                    "summary": "林澈在旧城区保管铜钥匙。",
                    "characters": ["林澈"],
                    "objects": ["铜钥匙"],
                    "location": "旧城区",
                }
            ],
            source_revision_id="rev-1",
        )
        return store

    def test_reports_location_holder_and_hidden_secret_with_evidence(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-") as raw_root:
            root = Path(raw_root)
            self._store(root)
            text = "林澈在白塔医院握着铜钥匙，沈砚站在旁边。\n有人提到了父亲身份。"

            result = check_event_consistency(
                text,
                root,
                chapter_id="002",
                plan={"scenes": [{"location": "白塔医院"}]},
                state_update={},
            )

            types = {item["type"] for item in result["findings"]}
            self.assertIn("character_location_conflict", types)
            self.assertIn("object_holder_conflict", types)
            self.assertIn("hidden_secret_knowledge_leak", types)
            self.assertTrue(all(item["evidence"] for item in result["findings"]))
            self.assertTrue(result["pass"])
            self.assertFalse(result["blocking"])

    def test_state_updates_suppress_expected_location_and_holder_changes(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-safe-") as raw_root:
            root = Path(raw_root)
            self._store(root)
            text = "林澈在白塔医院把铜钥匙交给沈砚。"

            result = check_event_consistency(
                text,
                root,
                chapter_id="002",
                plan={"scenes": [{"location": "白塔医院"}]},
                state_update={
                    "characters": {
                        "林澈": {"location": "白塔医院"},
                        "沈砚": {"location": "白塔医院"},
                    },
                    "objects": [{"id": "key-1", "holder": "沈砚"}],
                    "secrets": [{"id": "secret-1", "status": "revealed"}],
                },
            )

            self.assertEqual(result["findings"], [])

    def test_quality_report_exposes_event_consistency_check(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-report-") as raw_root:
            root = Path(raw_root)
            self._store(root)
            chapter_dir = root / "workspace" / "chapters" / "chapter_002"
            chapter_dir.mkdir(parents=True)
            (chapter_dir / "plan.json").write_text(
                json.dumps({"scenes": [{"location": "白塔医院"}], "chapter_id": "002"}, ensure_ascii=False),
                encoding="utf-8",
            )
            report = build_quality_report(
                "林澈在白塔医院握着铜钥匙，沈砚站在旁边。",
                root_dir=root,
                chapter_id="002",
                audit={"state_update": {}},
            )

            check = report["checks"]["event_consistency"]
            self.assertIn("event_consistency", report["checks"])
            self.assertGreaterEqual(check["conflict_count"], 2)
            self.assertTrue(check["pass"])

    def test_reports_injury_conflict_and_story_time_regression(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-time-") as raw_root:
            root = Path(raw_root)
            store = self._store(root)
            store.upsert_narrative_events(
                "001",
                [
                    {
                        "id": "E_TIME_5",
                        "summary": "林澈在第五天抵达。",
                        "characters": ["林澈"],
                        "story_time": "第5天",
                    }
                ],
                source_revision_id="rev-time-5",
            )

            result = check_event_consistency(
                "林澈毫发无伤地站在门口。",
                root,
                chapter_id="002",
                state_update={
                    "events": [
                        {
                            "id": "E_TIME_3",
                            "summary": "林澈在第三天回到这里。",
                            "characters": ["林澈"],
                            "story_time": "第3天",
                        }
                    ]
                },
            )

            types = {item["type"] for item in result["findings"]}
            self.assertIn("character_injury_conflict", types)
            self.assertIn("story_time_regression", types)
            time_finding = next(item for item in result["findings"] if item["type"] == "story_time_regression")
            self.assertTrue(any(evidence.get("kind") == "narrative_event" for evidence in time_finding["evidence"]))

    def test_reports_unanchored_abrupt_turn_for_new_entities(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-turn-") as raw_root:
            root = Path(raw_root)
            self._store(root)

            result = check_event_consistency(
                "突然出现一名陌生人，手里握着黑盒。",
                root,
                chapter_id="002",
                state_update={
                    "events": [
                        {
                            "id": "E_TURN",
                            "summary": "突然出现一名陌生人，手里握着黑盒。",
                            "characters": ["陌生人"],
                            "objects": ["黑盒"],
                            "threads": [],
                            "causes": [],
                        }
                    ]
                },
            )

            finding = next(item for item in result["findings"] if item["type"] == "unanchored_turn")
            self.assertEqual(finding["severity"], "medium")
            self.assertFalse(finding["blocking"])
            self.assertTrue(any(item.get("kind") == "anchor_check" for item in finding["evidence"]))

    def test_existing_entity_or_cause_anchor_suppresses_abrupt_turn(self):
        with tempfile.TemporaryDirectory(prefix="event-consistency-turn-safe-") as raw_root:
            root = Path(raw_root)
            self._store(root)

            anchored = check_event_consistency(
                "没想到林澈早已打开了暗门。",
                root,
                chapter_id="002",
                state_update={
                    "events": [
                        {
                            "id": "E_TURN_SAFE",
                            "summary": "没想到林澈早已打开了暗门。",
                            "characters": ["林澈"],
                            "objects": ["暗门"],
                            "causes": [],
                        }
                    ]
                },
            )
            self.assertNotIn("unanchored_turn", {item["type"] for item in anchored["findings"]})

            caused = check_event_consistency(
                "原来黑盒一直藏在门后。",
                root,
                chapter_id="002",
                state_update={
                    "events": [
                        {
                            "id": "E_TURN_CAUSED",
                            "summary": "原来黑盒一直藏在门后。",
                            "characters": ["陌生人"],
                            "objects": ["黑盒"],
                            "causes": ["E001"],
                        }
                    ]
                },
            )
            self.assertNotIn("unanchored_turn", {item["type"] for item in caused["findings"]})


if __name__ == "__main__":
    unittest.main()
