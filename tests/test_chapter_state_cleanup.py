"""Chapter delete cascade cleanup."""

import tempfile
import unittest
from pathlib import Path

from novel_agent.state.sqlite_store import SQLiteStateStore


class ChapterStateCleanupTests(unittest.TestCase):
    def test_delete_chapter_clears_globals_not_in_remaining_events(self):
        tmp = Path(tempfile.mkdtemp(prefix="ch-cleanup-"))
        try:
            store = SQLiteStateStore(tmp)
            store.sync_state_update("001", {
                "events": [{"id": "E001", "summary": "stay"}],
                "characters": {"主角": {"name": "主角", "location": "A", "emotion": "ok"}},
                "objects": [{"id": "O001", "name": "保留物"}],
            })
            store.sync_state_update("002", {
                "events": [{"id": "E002", "summary": "gone"}],
                "characters": {"配角甲": {"name": "配角甲", "location": "B", "emotion": "x"}},
                "objects": [{"id": "O002", "name": "删除物"}],
                "threads": [{"id": "T002", "title": "线", "status": "open", "summary": "s"}],
            })
            store.index_chapter("001", "第一章", tmp / "a.txt", 100, "")
            store.index_chapter("002", "第二章", tmp / "b.txt", 100, "")
            (tmp / "assets").mkdir(exist_ok=True)
            (tmp / "assets" / "character_cards.yaml").write_text(
                "characters:\n  - id: protagonist\n    name: 主角\n",
                encoding="utf-8",
            )

            store.delete_chapter_index("002")

            self.assertIn("主角", store.list_characters())
            self.assertNotIn("配角甲", store.list_characters())
            # O001 only exists via sync, not event JSON — kept while chapter 001 remains
            self.assertEqual([o["id"] for o in store.list_objects()], ["O001"])
            self.assertEqual(store.list_threads(), [])

            store.delete_chapter_index("001")
            self.assertEqual(store.list_objects(), [])
            # Protagonist from character_cards is kept as protected cast
            self.assertEqual(set(store.list_characters().keys()), {"主角"})
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()