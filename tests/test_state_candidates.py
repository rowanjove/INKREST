import json
import sqlite3
import tempfile
import unittest
import shutil
from pathlib import Path

from novel_agent.state.manager import StateManager
from novel_agent.state.sqlite_store import SQLiteStateStore, safe_connection


class StateCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-candidates-test-"))
        self.state_dir = self.tmpdir / "state"
        self.state_dir.mkdir()
        (self.state_dir / "events.yaml").write_text("events: []\n", encoding="utf-8")
        (self.state_dir / "objects.yaml").write_text("objects: []\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_interactive_mode_can_hold_state_as_pending_when_auto_accept_is_disabled(self):
        manager = StateManager(self.tmpdir)
        update = {
            "events": [{"id": "E100", "summary": "主角找到了宝藏。"}],
            "objects": [{"id": "O_TREASURE", "name": "神秘宝藏", "holder": "主角", "status": "active"}]
        }
        
        # 1. 交互模式写入 (interactive=True)
        manager.apply_update("001", update, interactive=True, auto_accept=False)
        
        # 2. 验证主生产表此时应该依然为空（未直接落库）
        events = manager.store.search_events("宝藏", limit=5)
        self.assertEqual(len(events), 0)
        
        # 3. 验证 YAML 文件同样不应有新状态写入
        yaml_content = (self.state_dir / "events.yaml").read_text(encoding="utf-8")
        self.assertNotIn("E100", yaml_content)
        
        # 4. 验证 candidates 暂存表中应该存在状态，且 status 为 'pending'
        candidates = manager.store.list_state_change_candidates(chapter_id="001", status="pending")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["entity_type"], "event")
        self.assertEqual(candidates[0]["entity_id"], "E100")
        self.assertEqual(candidates[1]["entity_type"], "object")
        self.assertEqual(candidates[1]["entity_id"], "O_TREASURE")
        self.assertEqual(candidates[1]["status"], "pending")

    def test_non_interactive_mode_accepts_and_writes_immediately(self):
        manager = StateManager(self.tmpdir)
        update = {
            "events": [{"id": "E101", "summary": "主角打开了宝箱。"}],
            "objects": [{"id": "O_CHEST", "name": "白银宝箱", "holder": "主角", "status": "opened"}]
        }
        
        # 1. 非交互模式写入 (interactive=False)
        manager.apply_update("002", update, interactive=False)
        
        # 2. 验证直接应用到生产表
        events = manager.store.search_events("宝箱", limit=5)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "E101")
        
        objects = manager.store.list_objects()
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["id"], "O_CHEST")
        
        # 3. 验证 YAML 正常同步写入
        yaml_content = (self.state_dir / "events.yaml").read_text(encoding="utf-8")
        self.assertIn("E101", yaml_content)
        
        # 4. 验证 candidates 表中存在记录且 status 为 'accepted'
        candidates = manager.store.list_state_change_candidates(chapter_id="002", status="accepted")
        self.assertEqual(len(candidates), 2)

    def test_interactive_mode_auto_accepts_by_default(self):
        manager = StateManager(self.tmpdir)
        update = {
            "events": [{"id": "E_AUTO", "summary": "设定自动同步。"}],
        }

        manager.apply_update("002-auto", update, interactive=True)

        self.assertEqual(len(manager.store.search_events("自动同步", limit=5)), 1)
        self.assertEqual(len(manager.store.list_state_change_candidates(chapter_id="002-auto", status="pending")), 0)
        self.assertEqual(len(manager.store.list_state_change_candidates(chapter_id="002-auto", status="accepted")), 1)

    def test_approve_all_candidates_flushes_pending_to_db(self):
        manager = StateManager(self.tmpdir)
        update = {
            "events": [{"id": "E102", "summary": "主角学会了御剑飞行。"}],
            "characters": {"主角": {"location": "青云山", "emotion": "兴奋"}}
        }
        
        # 交互模式，首先暂存为 pending
        manager.apply_update("003", update, interactive=True, auto_accept=False)
        
        # 此时接受本章全部 pending 状态更新
        manager.store.accept_chapter_candidates("003")
        
        # 验证核心主生产表应有状态
        events = manager.store.search_events("御剑", limit=5)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "E102")
        
        chars = manager.store.list_characters()
        self.assertIn("主角", chars)
        self.assertEqual(chars["主角"]["location"], "青云山")
        
        # 验证暂存表状态已刷为 accepted
        pending_cands = manager.store.list_state_change_candidates(chapter_id="003", status="pending")
        self.assertEqual(len(pending_cands), 0)
        accepted_cands = manager.store.list_state_change_candidates(chapter_id="003", status="accepted")
        self.assertEqual(len(accepted_cands), 2)

    def test_approve_single_candidate(self):
        manager = StateManager(self.tmpdir)
        update = {
            "events": [{"id": "E103", "summary": "事件一。"}],
            "objects": [{"id": "O_SWORD", "name": "斩妖剑", "holder": "主角", "status": "active"}]
        }
        
        manager.apply_update("004", update, interactive=True, auto_accept=False)
        candidates = manager.store.list_state_change_candidates(chapter_id="004", status="pending")
        self.assertEqual(len(candidates), 2)
        
        # 单独批准 O_SWORD
        sword_cand = [c for c in candidates if c["entity_type"] == "object"][0]
        manager.store.accept_candidate(sword_cand["id"])
        
        # 验证 objects 主表有数据，而 events 表依旧空
        objects = manager.store.list_objects()
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["id"], "O_SWORD")
        
        events = manager.store.search_events("事件一", limit=5)
        self.assertEqual(len(events), 0)
        
        # 验证仅有一个 accepted 和一个 pending
        self.assertEqual(len(manager.store.list_state_change_candidates(chapter_id="004", status="accepted")), 1)
        self.assertEqual(len(manager.store.list_state_change_candidates(chapter_id="004", status="pending")), 1)

    def test_tasks_table_migration_and_updates(self):
        store = SQLiteStateStore(self.tmpdir)
        
        # 验证 tasks 表是否成功拓宽了 current_step、pipeline_version、updated_at 字段
        with safe_connection(store.db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("pragma table_info(tasks)").fetchall()
            }
            self.assertIn("current_step", columns)
            self.assertIn("pipeline_version", columns)
            self.assertIn("updated_at", columns)
            
        # 模拟保存 task，并写入 progress updates
        task_id = "test-task-1"
        store.save_task(task_id, "001", "生成第001章", False, "pending")
        
        store.update_task_progress(task_id, {"step": "planner", "status": "running"})
        
        # 验证 tasks 对应的字段发生了改变
        task = store.get_task(task_id)
        self.assertEqual(task["current_step"], "planner")
        self.assertEqual(task["pipeline_version"], "Chapter Pipeline v1.0")
        
        # 手动更新 step 动作
        store.update_task_step(task_id, "writer")
        task = store.get_task(task_id)
        self.assertEqual(task["current_step"], "writer")


if __name__ == "__main__":
    unittest.main()
