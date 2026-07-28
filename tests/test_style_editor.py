import unittest
import asyncio
from unittest.mock import MagicMock
from novel_agent.agents.style_editor import StyleEditorAgent

class TestStyleEditorAgent(unittest.TestCase):
    def setUp(self):
        # 1. 构造一个 mock LLM
        self.mock_llm = MagicMock()
        # 默认同步的 generate 返回被调用的 role / prompt（或者固定格式，这里我们为了测试拼接，让其直接返回修改后标识）
        self.mock_llm.generate.side_effect = lambda role, prompt: f"Polished: {prompt.split('=== 待润色片段 ===')[-1].split('===')[0].strip()}" if "=== 待润色片段 ===" in prompt else f"Polished: {prompt.split(role)[-1].strip()}"
        
        # 异步的 agenerate
        async def mock_agenerate(role, prompt):
            if "=== 待润色片段 ===" in prompt:
                target = prompt.split("=== 待润色片段 ===")[-1].split("===")[0].strip()
                return f"Polished: {target}"
            return f"Polished: {prompt.split(role)[-1].strip()}"
        self.mock_llm.agenerate = mock_agenerate

        self.agent = StyleEditorAgent(self.mock_llm)
        self.agent.max_chunk_chars = 40  # 把限制调小，方便用小文本触发分段

    def test_short_text_no_split(self):
        # 长度小于 100 的文本不应该触发分段
        text = "这是一段很短的正文。不需要被拆分。"
        res = self.agent.edit(text)
        self.mock_llm.generate.assert_called_once()
        self.assertIn("Polished:", res)
        # 应该是不含 "=== 待润色片段 ===" 的常规 prompt
        called_prompt = self.mock_llm.generate.call_args[0][1]
        self.assertNotIn("=== 待润色片段 ===", called_prompt)

    def test_long_text_triggers_split_sync(self):
        # 构造三段文本，每一段的长度大约是 40-50 个字符。总长度会超出 max_chunk_chars = 100
        p1 = "第一段文本，描写主角在寒冷风中的站立，身姿挺拔如松树一般。"
        p2 = "第二段文本，描写主角面前出现了一头巨大的野兽，他握紧了拳头。"
        p3 = "第三段文本，主角一剑斩出，寒光照亮了黑夜，野兽轰然倒地。"
        text = f"{p1}\n\n{p2}\n\n{p3}"
        
        res = self.agent.edit(text)
        
        # 因为 max_chunk_chars = 100，三段加起来 ~110 字，
        # 只要 generate 被调用了多次（> 1），就说明分段被触发了。
        self.assertTrue(self.mock_llm.generate.call_count > 1)
        
        # 验证最终合并出来的文本，格式正常，且每一段都经过了 Polished 润色
        paragraphs = res.split("\n\n")
        self.assertTrue(len(paragraphs) >= 2)
        for p in paragraphs:
            self.assertTrue(p.startswith("Polished: "))

        # 检查传给 LLM 的 prompt 是否包含上下文衔接
        # 最后一个调用的 prompt 应该包含 "=== 前文参考" 或者是 "=== 后文参考"
        last_called_prompt = self.mock_llm.generate.call_args_list[-1][0][1]
        self.assertIn("=== 前文参考", last_called_prompt)
        self.assertIn("=== 待润色片段 ===", last_called_prompt)

    async def _async_test_long_text_triggers_split(self):
        # 异步测试分段
        p1 = "第一段文本，描写主角在寒冷风中的站立，身姿挺拔如松树一般。"
        p2 = "第二段文本，描写主角面前出现了一头巨大的野兽，他握紧了拳头。"
        p3 = "第三段文本，主角一剑斩出，寒光照亮了黑夜，野兽轰然倒地。"
        text = f"{p1}\n\n{p2}\n\n{p3}"
        
        # 跟踪 agenerate 是否被调用
        original_agenerate = self.mock_llm.agenerate
        call_count = 0
        async def tracking_agenerate(role, prompt):
            nonlocal call_count
            call_count += 1
            return await original_agenerate(role, prompt)
        self.mock_llm.agenerate = tracking_agenerate

        res = await self.agent.aedit(text)
        
        self.assertTrue(call_count > 1)
        paragraphs = res.split("\n\n")
        self.assertTrue(len(paragraphs) >= 2)
        for p in paragraphs:
            self.assertTrue(p.startswith("Polished: "))

    def test_long_text_triggers_split_async(self):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(asyncio.run, self._async_test_long_text_triggers_split()).result()
        else:
            asyncio.run(self._async_test_long_text_triggers_split())

if __name__ == "__main__":
    unittest.main()
