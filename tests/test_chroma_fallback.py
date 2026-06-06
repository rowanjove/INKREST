import unittest
import tempfile
import shutil
from pathlib import Path
from novel_agent.state.vector_store import (
    create_vector_store,
    VectorChunk,
    CHROMA_AVAILABLE,
)

class TestChromaFallback(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-chroma-test-"))

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_chroma_backend_config_routing(self):
        # 1. 测试即使配置 backend 为 chromadb，若 CHROMA_AVAILABLE 为 False，也能正常退回到 SQLite 并运行
        # 我们可以通过 mock 或者是即使当前没有安装 chromadb，它也不会崩溃
        config = {
            "provider": "stub",
            "backend": "chromadb"
        }
        
        # 无论 chromadb 是否安装，这里都不应该抛出异常
        store = create_vector_store(config, root_dir=self.tmpdir)
        self.assertIsNotNone(store)
        
        # 增删改查基本测试
        chunks = [
            VectorChunk(id="c1", type="chapter_summary", text="萧炎修炼斗之气。", metadata={"chapter": 1}),
            VectorChunk(id="c2", type="prose_chunk", text="纳兰嫣然前来退婚。", metadata={"chapter": 2})
        ]
        store.upsert(chunks)
        
        results = store.search(query="退婚", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "c2")

    def test_chromadb_real_execution(self):
        # 2. 如果当前环境中装有 chromadb，我们测试它真正的执行通路
        if not CHROMA_AVAILABLE:
            self.skipTest("chromadb is not installed in the testing environment, skipping real chroma execution test.")
            
        config = {
            "provider": "stub",
            "backend": "chromadb"
        }
        store = create_vector_store(config, root_dir=self.tmpdir)
        self.assertIsNotNone(store.chroma_collection)  # 此时不应该是 None
        
        chunks = [
            VectorChunk(id="c1", type="chapter_summary", text="萧炎修炼斗之气。", metadata={"chapter": 1}),
            VectorChunk(id="c2", type="prose_chunk", text="纳兰嫣然前来退婚。", metadata={"chapter": 2})
        ]
        store.upsert(chunks)
        
        # 验证 chromadb 里面确实写入了数据
        self.assertEqual(store.chroma_collection.count(), 2)
        
        # 验证 search 从 chromadb 召回
        results = store.search(query="退婚", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "c2")
        
        # 验证 delete
        store.delete(["c1"])
        self.assertEqual(store.chroma_collection.count(), 1)

if __name__ == "__main__":
    unittest.main()
