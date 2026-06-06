import os
import tempfile
import unittest
from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch

from novel_agent.prompts import PromptRepository
from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.agents.base import OpenAILLM
from novel_agent.state.vector_store import SQLiteEmbeddingVectorStore, VectorChunk, create_vector_store


class TestLocalizationAndContext(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="novel-agent-test-l10n-"))
        self.db_path = self.tmpdir / "data" / "novel.sqlite"

    def tearDown(self):
        import gc
        gc.collect()
        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            pass

    def test_prompt_repository_fallback_chain(self):
        repo = PromptRepository(self.tmpdir)
        
        # 1. 尝试加载不存在的角色，应该返回空字符串
        self.assertEqual(repo.load("non_existent_role"), "")
        
        # 2. 模拟环境变量 Fallback
        env_dir = self.tmpdir / "env_templates"
        prompts_dir = env_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "test_role.md").write_text("env_content", encoding="utf-8")
        
        with patch.dict(os.environ, {"NOVEL_AGENT_TEMPLATES": str(env_dir)}):
            self.assertEqual(repo.load("test_role"), "env_content")
            
        # 清除缓存测试本地项目覆盖
        repo.clear_cache()
        local_prompts = self.tmpdir / "prompts"
        local_prompts.mkdir(parents=True, exist_ok=True)
        (local_prompts / "test_role.md").write_text("local_content", encoding="utf-8")
        
        # 优先读取本地项目模板
        self.assertEqual(repo.load("test_role"), "local_content")

    def test_context_builder_token_estimation(self):
        builder = ContextBuilderAgent(self.tmpdir)
        
        # 测试 Token 估算：纯中文
        text_cn = "测试分词"
        estimated_cn = builder._estimate_tokens(text_cn)
        self.assertGreater(estimated_cn, 0)
        
        # 测试 Token 估算：纯英文
        text_en = "hello world test"
        estimated_en = builder._estimate_tokens(text_en)
        self.assertGreater(estimated_en, 0)

    def test_context_builder_budget_trimming(self):
        # 强制设置非常小的 Token 预算，如 30 Tokens
        builder = ContextBuilderAgent(self.tmpdir)
        builder.max_context_tokens = 30
        
        # 构造一块很大的高优先级 block 和一块中优先级 block
        blocks = [
            ("关键场景", "这是非常关键的场景正文，不能被裁剪。", 0), # PRIORITY_CRITICAL
            ("世界观设定", "这是一段冗长且不那么重要的低优先级设定背景资料，因为超预算应当被裁剪掉。", 3), # PRIORITY_LOW
        ]
        
        assembled = builder._assemble_with_budget(blocks)
        # critical 必须存在
        self.assertIn("关键场景", assembled)
        # 低优先级应当被裁剪/丢弃
        self.assertNotIn("不那么重要的低优先级设定背景资料", assembled)

    @patch('httpx.Client.post')
    def test_llm_context_budget_test_interface(self, mock_post):
        # 模拟大模型成功测试
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "TEST_SECRET_BUDGET_OK_9981"}}],
            "model": "mock-model"
        }
        mock_post.return_value = mock_response
        
        llm = OpenAILLM(base_url="https://api.openai.com/v1", api_key="test-key", model="mock-model")
        res = llm.test_context_budget(100)
        
        self.assertTrue(res["success"])
        self.assertTrue(bool(res.get("message")))

    def test_vector_store_mode_detection_and_fallback(self):
        # 配置 provider 为 local (但在测试中没有 ONNX 文件和 onnxruntime，应当安全降级至 Stub)
        config = {
            "provider": "local",
            "model_path": str(self.tmpdir / "non_existent.onnx")
        }
        
        store = create_vector_store(config, root_dir=self.tmpdir)
        
        # 即使 ONNX 文件缺失，upsert 也不应该崩溃崩溃，应静默降级为 Stub
        chunk = VectorChunk(id="c1", type="scene_summary", text="测试剧情", metadata={})
        try:
            store.upsert([chunk])
            success = True
        except Exception:
            success = False
            
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
