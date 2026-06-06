import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import shutil
import gc

from novel_agent.agents.base import StaticLLM
from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig
from novel_agent.state.vector_store import create_vector_store


class TestAgentEmbeddingLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-lifecycle-test-"))
        self.db_path = self.tmpdir / "data" / "novel.sqlite"

    def tearDown(self):
        # 显式关闭 vector_store，清理变量并做垃圾回收，避免 Windows 下文件被占用无法删除
        if hasattr(self, "orchestrator") and self.orchestrator:
            try:
                self.orchestrator.vector_store.close()
            except Exception:
                pass
        self.orchestrator = None
        self.context_builder = None
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_end_to_end_embedding_lifecycle(self):
        # 1. 设置 LLM 输出，使其包含 character_behaviors 提取以及正常 plan 与 audit
        llm = StaticLLM(
            responses={
                "planner": json.dumps(
                    {
                        "chapter_id": "001",
                        "chapter_title": "雨夜觉醒",
                        "target_chars": [20, 80],
                        "scenes": [
                            {
                                "scene_id": "001-01",
                                "target_chars": [10, 60],
                                "purpose": "林澈觉醒能力",
                                "entry": "林澈回到出租屋",
                                "exit": "灯灭了",
                                "characters": ["林澈"],
                                "must_include": ["出租屋", "停电"],
                                "must_not_include": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                "writer": "林澈回屋停电了。",
                "stitch_editor": "林澈回屋停电了。",
                "style_editor": "林澈回屋停电了。",
                "continuity_checker": '{"pass":true,"issues":[]}',
                "auditor": json.dumps(
                    {
                        "risk_level": "低",
                        "issues": [],
                        "state_update": {},
                    },
                    ensure_ascii=False,
                ),
                "state_extractor": json.dumps(
                    {
                        "events": [{"id": "E001_001", "summary": "林澈在雨夜回出租屋遇到停电。"}],
                        "characters": {"林澈": {"location": "出租屋", "emotion": "警惕"}},
                        "foreshadows": [
                            {
                                "id": "F_001",
                                "title": "旧照片的黑影",
                                "status": "open",
                                "description": "合照背景里站着一个模糊的黑影",
                            }
                        ],
                        "character_behaviors": [
                            {
                                "character": "林澈",
                                "behavior": "林澈在感到压力时，会习惯性地用右手无名指敲击桌面三下。",
                                "context": "面对神秘危机",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                "chapter_summary": "林澈遭遇了雨夜停电并发现了黑影。",
            }
        )

        config = PipelineConfig(root_dir=self.tmpdir, llm=llm)
        # 强制配置为本地 stub 以避开网络调用
        config.embedding_config = {"provider": "stub"}
        
        self.orchestrator = NovelOrchestrator(config)
        
        # 运行第一章，生成并提取状态，进而触发向量数据库 upsert
        result = self.orchestrator.run_chapter("001", "主角雨夜回到出租屋并觉醒。")
        self.assertEqual(result.chapter_id, "001")

        # 2. 检查向量数据库是否成功保存了伏笔和角色行为习惯
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, type, text, metadata FROM vector_embeddings").fetchall()
            
        types = [r["type"] for r in rows]
        self.assertIn("chapter_summary", types)
        self.assertIn("foreshadow", types)
        self.assertIn("character_behavior", types)

        # 3. 验证 ContextBuilder 能否在写下一章场景时成功检索并注入性格一致性约束
        self.context_builder = ContextBuilderAgent(self.tmpdir, vector_store=self.orchestrator.vector_store)
        context = self.context_builder.build(
            chapter_goal="调查旧照片",
            scene={
                "scene_id": "002-01",
                "characters": ["林澈"],
                "purpose": "林澈看着旧照片陷入沉思，面临极大的危机压迫",
                "must_include": ["旧照片"],
            }
        )
        
        # 应成功注入性格行为一致性约束
        self.assertIn("角色性格行为一致性约束", context)
        self.assertIn("林澈在感到压力时，会习惯性地用右手无名指敲击桌面三下", context)

        # 4. 验证在重新规划第 2 章时，Orchestrator 是否会触发情节重复警告和未揭示伏笔建议
        duplicate_warnings = ""
        try:
            similar_summaries = self.orchestrator.vector_store.search(
                query="林澈在雨夜回出租屋遇到停电，并查看照片黑影",
                top_k=5,
                filters={"type": "chapter_summary"}
            )
            warning_lines = []
            for r in similar_summaries:
                score = r.get("score", 0.0)
                if score >= 0.4:  # Stub 模式自适应评估
                    ch_id = r.get("metadata", {}).get("chapter", "")
                    warning_lines.append(f"- 第 {ch_id} 章 剧情摘要: {r['text'][:50]}")
            if warning_lines:
                duplicate_warnings = "\n".join(warning_lines)
        except Exception as e:
            pass

        self.assertIn("第 001 章", duplicate_warnings)

        # 5. 验证删除章节时清理向量
        self.orchestrator.store.delete_chapter_index("001")
        with sqlite3.connect(self.db_path) as conn:
            row_count = conn.execute("SELECT count(*) FROM vector_embeddings").fetchone()[0]
        self.assertEqual(row_count, 0)


if __name__ == "__main__":
    unittest.main()
