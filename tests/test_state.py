import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import shutil

from novel_agent.state.manager import StateManager
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-state-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_state_manager_merges_events_and_writes_snapshot(self):
        state_dir = self.tmpdir / "state"
        state_dir.mkdir()
        (state_dir / "events.yaml").write_text("events: []\n", encoding="utf-8")
        manager = StateManager(self.tmpdir)
        manager.apply_update(
            "001",
            {"events": [{"id": "E001", "summary": "主角遭遇停电。"}]},
        )
        events_text = (state_dir / "events.yaml").read_text(encoding="utf-8")
        self.assertIn("E001", events_text)
        self.assertTrue((state_dir / "snapshots" / "chapter_001").exists())

    def test_sqlite_state_store_syncs_and_queries_events(self):
        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update(
            "012",
            {
                "events": [
                    {
                        "id": "E012_003",
                        "summary": "林澈播放录音笔，听到白塔医院。",
                        "characters": ["林澈"],
                        "objects": ["黑色录音笔"],
                        "threads": ["T001"],
                    }
                ]
            },
        )
        results = store.search_events("白塔医院", limit=5)
        self.assertEqual(results[0]["id"], "E012_003")
        self.assertEqual(results[0]["chapter_id"], "012")
        self.assertIn("黑色录音笔", results[0]["objects"])

    def test_sqlite_state_store_syncs_and_queries_timeline_network(self):
        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update(
            "012",
            {
                "timeline_nodes": [
                    {
                        "id": "N_WHITE_TOWER",
                        "type": "setting",
                        "name": "白塔医院",
                        "description": "父亲死亡真相相关地点。",
                    }
                ],
                "timeline_edges": [
                    {
                        "id": "EDGE_RECORDER_HOSPITAL",
                        "from": "黑色录音笔",
                        "to": "白塔医院",
                        "type": "points_to",
                        "description": "录音笔线索指向白塔医院。",
                    }
                ],
                "foreshadows": [
                    {
                        "id": "F001",
                        "title": "白塔医院地下二层",
                        "status": "open",
                        "description": "建筑图纸里不存在的楼层。",
                    }
                ],
                "hooks": [
                    {
                        "id": "H001",
                        "title": "门外父亲声音",
                        "status": "open",
                        "description": "死去父亲的声音在门外响起。",
                    }
                ],
            },
        )
        results = store.search_timeline("白塔医院", limit=10)
        result_ids = {item["id"] for item in results}
        self.assertIn("N_WHITE_TOWER", result_ids)
        self.assertIn("F001", result_ids)
        self.assertIn("EDGE_RECORDER_HOSPITAL", result_ids)

    def test_state_manager_updates_sqlite_mirror(self):
        state_dir = self.tmpdir / "state"
        state_dir.mkdir()
        (state_dir / "events.yaml").write_text("events: []\n", encoding="utf-8")
        StateManager(self.tmpdir).apply_update(
            "004",
            {"events": [{"id": "E004", "summary": "白塔医院第一次出现。"}]},
        )
        db_path = self.tmpdir / "data" / "novel.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("select summary from events where id = ?", ("E004",)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "白塔医院第一次出现。")

    def test_sqlite_store_creates_narrative_debt_tables(self):
        store = SQLiteStateStore(self.tmpdir)
        with safe_connection(store.db_path) as conn:
            conn.execute("select count(*) from reader_promises")
            conn.execute("select count(*) from secrets")

    def test_sqlite_store_upserts_and_lists_reader_promises(self):
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_reader_promise({
            "id": "RP_001",
            "title": "主角会找到父亲",
            "status": "open",
            "description": "读者期待主角找到父亲的真相",
            "chapter_id": "001",
        })
        store.upsert_reader_promise({
            "id": "RP_002",
            "title": "神秘组织的阴谋",
            "status": "open",
            "description": "读者期待揭露神秘组织的阴谋",
            "chapter_id": "002",
        })
        promises = store.list_reader_promises()
        self.assertEqual(len(promises), 2)
        self.assertEqual(promises[0]["id"], "RP_001")
        open_promises = store.list_reader_promises(status="open")
        self.assertEqual(len(open_promises), 2)

    def test_sqlite_store_upserts_and_lists_secrets(self):
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_secret({
            "id": "SEC_001",
            "title": "父亲的真实身份",
            "status": "hidden",
            "description": "父亲其实是组织的卧底",
            "chapter_id": "001",
        })
        secrets = store.list_secrets()
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["id"], "SEC_001")
        hidden_secrets = store.list_secrets(status="hidden")
        self.assertEqual(len(hidden_secrets), 1)
        open_secrets = store.list_secrets(status="open")
        self.assertEqual(len(open_secrets), 0)

    def test_sqlite_store_preserves_deadline_metadata_for_foreshadows(self):
        store = SQLiteStateStore(self.tmpdir)
        store.sync_state_update("001", {
            "foreshadows": [{
                "id": "F001",
                "title": "短信号码",
                "status": "open",
                "description": "未知号码发来提醒",
                "deadline_chapter": "010",
                "related_characters": ["沈星璃"],
            }]
        })
        item = store.list_foreshadows()[0]
        self.assertEqual(item["deadline_chapter"], "010")
        self.assertEqual(item["related_characters"], ["沈星璃"])

    def test_delete_chapter_index_removes_narrative_debt_rows(self):
        store = SQLiteStateStore(self.tmpdir)
        store.upsert_reader_promise({
            "id": "RP_001",
            "title": "promise",
            "status": "open",
            "description": "",
            "chapter_id": "001",
        })
        store.upsert_secret({
            "id": "SEC_001",
            "title": "secret",
            "status": "hidden",
            "description": "",
            "chapter_id": "001",
        })
        store.delete_chapter_index("001")
        self.assertEqual(store.list_reader_promises(), [])
        self.assertEqual(store.list_secrets(), [])

    def test_narrative_debt_marks_overdue_items(self):
        from novel_agent.control.narrative_debt import classify_debt
        items = [{"id": "F001", "status": "open", "deadline_chapter": "010", "title": "短信号码"}]
        result = classify_debt(items, current_chapter="012")
        self.assertEqual(result[0]["debt_status"], "overdue")

    def test_sqlite_concurrency(self):
        import concurrent.futures
        store = SQLiteStateStore(self.tmpdir)
        
        def write_task(i):
            store.upsert_reader_promise({
                "id": f"RP_CONC_{i}",
                "title": f"promise {i}",
                "status": "open",
                "description": "concurrent testing",
                "chapter_id": "001",
            })
            return i

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_task, i) for i in range(20)]
            results = [f.result() for f in futures]
            
        promises = store.list_reader_promises()
        self.assertEqual(len([p for p in promises if "RP_CONC_" in p["id"]]), 20)

    def test_version_history_tables(self):
        store = SQLiteStateStore(self.tmpdir)
        with safe_connection(store.db_path) as conn:
            conn.execute(
                "insert into prompt_versions (role, content, version, note) values (?, ?, ?, ?)",
                ("writer", "Write a chapter...", 1, "Initial test prompt")
            )
            row = conn.execute("select content, version, note from prompt_versions where role='writer'").fetchone()
            self.assertEqual(row[0], "Write a chapter...")
            self.assertEqual(row[1], 1)
            self.assertEqual(row[2], "Initial test prompt")
            
            conn.execute(
                "insert into asset_versions (asset_name, content, version, note) values (?, ?, ?, ?)",
                ("character_cards", "Char data...", 2, "Updated cards")
            )
            row = conn.execute("select content, version, note from asset_versions where asset_name='character_cards'").fetchone()
            self.assertEqual(row[0], "Char data...")
            self.assertEqual(row[1], 2)
            
            conn.execute(
                "insert into chapter_rewrites (chapter_id, version, content, word_count, rewrite_reason) values (?, ?, ?, ?, ?)",
                ("001", 1, "Chapter one text...", 1500, "Too short")
            )
            row = conn.execute("select content, word_count, rewrite_reason from chapter_rewrites where chapter_id='001'").fetchone()
            self.assertEqual(row[0], "Chapter one text...")
            self.assertEqual(row[1], 1500)
            self.assertEqual(row[2], "Too short")

            conn.execute(
                "insert into llm_cost_log (call_id, model, input_tokens, output_tokens, input_cost_cny, output_cost_cny, project_id) values (?, ?, ?, ?, ?, ?, ?)",
                ("call_999", "gpt-4", 100, 200, 0.001, 0.003, "proj_abc")
            )
            row = conn.execute("select model, input_tokens, output_tokens from llm_cost_log where call_id='call_999'").fetchone()
            self.assertEqual(row[0], "gpt-4")
            self.assertEqual(row[1], 100)
            self.assertEqual(row[2], 200)


if __name__ == "__main__":
    unittest.main()
