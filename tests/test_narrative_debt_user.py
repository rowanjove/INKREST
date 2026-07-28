import unittest
import tempfile
import shutil
from pathlib import Path
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.control.narrative_debt import classify_debt
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig

class TestNarrativeDebtUser(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-debt-test-"))
        self.store = SQLiteStateStore(self.tmpdir)

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_classify_debt_default_periods(self):
        # 1. 测试未提供 deadline_chapter 时，根据 default_period 自动计算
        items = [
            {"id": "d1", "chapter_id": "002", "status": "open", "deadline_chapter": ""}
        ]
        
        # default_period = 3 (承诺) -> deadline = 5
        res_promise = classify_debt(items, current_chapter="002", default_period=3)
        self.assertEqual(res_promise[0]["deadline_chapter"], "5")
        self.assertEqual(res_promise[0]["debt_status"], "open") # 2 < 5-2

        # current = 4 -> due_soon
        res_promise_soon = classify_debt(items, current_chapter="4", default_period=3)
        self.assertEqual(res_promise_soon[0]["debt_status"], "due_soon")

        # current = 6 -> overdue
        res_promise_overdue = classify_debt(items, current_chapter="6", default_period=3)
        self.assertEqual(res_promise_overdue[0]["debt_status"], "overdue")

    def test_classify_debt_user_priority(self):
        # 2. 测试 user_priority 置顶
        items = [
            {"id": "d1", "chapter_id": "002", "status": "open", "deadline_chapter": "10", "user_priority": 1}
        ]
        
        # 即使当前是 3，距离 10 还很远，但因为 user_priority = 1，所以状态提升为 overdue
        res = classify_debt(items, current_chapter="3", default_period=10)
        self.assertEqual(res[0]["debt_status"], "overdue")

    def test_sqlite_store_debt_apis(self):
        # 3. 测试 sqlite_store 的数据列更新接口
        promise = {"id": "p1", "title": "救回小明", "status": "open", "description": "带回小明"}
        self.store.upsert_reader_promise(promise)
        
        # 验证初始 user_priority 为 0
        promises = self.store.list_reader_promises()
        self.assertEqual(promises[0]["user_priority"], 0)
        self.assertEqual(promises[0]["plan_chapter"], "")

        # 调更新接口
        self.store.set_debt_priority("reader_promises", "p1", 5)
        self.store.set_debt_plan_chapter("reader_promises", "p1", "008")

        promises = self.store.list_reader_promises()
        self.assertEqual(promises[0]["user_priority"], 5)
        self.assertEqual(promises[0]["plan_chapter"], "008")

if __name__ == "__main__":
    unittest.main()
