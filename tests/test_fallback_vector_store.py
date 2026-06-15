import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import shutil
import numpy as np

from novel_agent.state.vector_store import (
    SQLiteEmbeddingVectorStore,
    VectorChunk,
    create_vector_store,
)


class TestFallbackVectorStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-vector-test-"))
        self.db_path = self.tmpdir / "data" / "novel.sqlite"

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_stub_search_tf_cosine_similarity(self):
        # 强制 stub 模式
        config = {"provider": "stub"}
        store = create_vector_store(config, root_dir=self.tmpdir)
        
        chunks = [
            VectorChunk(id="c1", type="chapter_summary", text="林澈在白塔医院调查父亲的死因。", metadata={"chapter": "001"}),
            VectorChunk(id="c2", type="chapter_summary", text="萧炎在魔兽山脉进行艰苦的修炼。", metadata={"chapter": "002"}),
            VectorChunk(id="c3", type="chapter_summary", text="林澈在白塔医院遇到了神秘医生。", metadata={"chapter": "003"}),
        ]
        store.upsert(chunks)

        # 语义检索：检索 "林澈 白塔医院"
        results = store.search(query="林澈 白塔医院", top_k=2, filters={"type": "chapter_summary"})
        self.assertEqual(len(results), 2)
        # 应包含 c1 和 c3，分数较高
        ids = {r["id"] for r in results}
        self.assertIn("c1", ids)
        self.assertIn("c3", ids)
        self.assertNotIn("c2", ids)

    def test_vector_search_mixed_dimensions_safety(self):
        # 创建数据库并直接手动向数据库插入不同维度的向量
        config = {"provider": "stub"}  # 虽然我们走 stub，但我们主要测试 _search_vector 的兼容性
        store = SQLiteEmbeddingVectorStore(config, root_dir=self.tmpdir)
        
        # 写入 1024 维向量和 1536 维向量
        vec_1024 = np.ones(1024, dtype=np.float32)
        vec_1024_blob = vec_1024.tobytes()
        
        vec_1536 = np.ones(1536, dtype=np.float32)
        vec_1536_blob = vec_1536.tobytes()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO vector_embeddings (id, type, text, embedding, metadata, chapter_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("id_1024", "prose_chunk", "文本1", vec_1024_blob, '{"chapter": "001"}', "001"),
            )
            conn.execute(
                "INSERT INTO vector_embeddings (id, type, text, embedding, metadata, chapter_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("id_1536", "prose_chunk", "文本2", vec_1536_blob, '{"chapter": "002"}', "002"),
            )
            conn.commit()
            
        # 1. 模拟用 1024 维 query_vec 去搜索
        query_1024 = np.ones(1024, dtype=np.float32)
        results = store._search_vector(query_1024, top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "id_1024")
        
        # 2. 模拟用 1536 维 query_vec 去搜索
        query_1536 = np.ones(1536, dtype=np.float32)
        results = store._search_vector(query_1536, top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "id_1536")

    def test_delete_chapter_vectors(self):
        config = {"provider": "stub"}
        store = create_vector_store(config, root_dir=self.tmpdir)
        
        chunks = [
            VectorChunk(id="v1", type="prose_chunk", text="文本1", metadata={"chapter": "005"}),
            VectorChunk(id="v2", type="prose_chunk", text="文本2", metadata={"chapter": "006"}),
            VectorChunk(id="v3", type="prose_chunk", text="文本3", metadata={"chapter": "005"}),
        ]
        store.upsert(chunks)
        
        # 删除第 5 章的向量
        store.delete_chapter_vectors("005")
        
        # 检索剩余向量
        results = store.search(query="文本", top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "v2")


if __name__ == "__main__":
    unittest.main()
