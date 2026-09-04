import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from novel_agent.agents.base import OpenAILLM
from novel_agent.exceptions import LLMThinkingTruncatedError, LLMResponseError, RetryExhaustedError
from novel_agent.phases.generation import GenerationPhase
from novel_agent.phases.base import ChapterContext


def test_process_response_raises_thinking_truncated_error():
    llm = OpenAILLM()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "",
                "reasoning_content": "Deep reasoning chain exceeding length..." * 50,
            },
            "finish_reason": "length",
        }],
        "usage": {"total_tokens": 8192},
    }

    with pytest.raises(LLMThinkingTruncatedError) as exc_info:
        llm._process_response(mock_resp, "writer", 0.0)

    assert "模型思考过程超限截断" in str(exc_info.value)


def test_generate_token_escalation_and_system_hint():
    llm = OpenAILLM(max_tokens=8192, max_retries=2, retry_delay=0.01)

    fail_resp = MagicMock()
    fail_resp.status_code = 200
    fail_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "",
                "reasoning_content": "Long thoughts...",
            },
            "finish_reason": "length",
        }],
        "usage": {"total_tokens": 8192},
    }

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "这是一段成功生成的场景正文。",
            },
            "finish_reason": "stop",
        }],
        "usage": {"total_tokens": 4500},
    }

    recorded_payloads = []

    def mock_post(url, headers, json):
        recorded_payloads.append(json)
        if len(recorded_payloads) == 1:
            return fail_resp
        return success_resp

    with patch.object(llm, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post.side_effect = mock_post
        mock_get_client.return_value = mock_client

        result = llm.generate("writer", "请写场景正文")

        assert result == "这是一段成功生成的场景正文。"
        assert len(recorded_payloads) == 2
        # Attempt 1 had initial max_tokens 8192
        assert recorded_payloads[0]["max_tokens"] == 8192
        # Attempt 2 escalated to 16384
        assert recorded_payloads[1]["max_tokens"] == 16384
        # Attempt 2 includes emergency concise-thinking directive
        assert "紧急生成指引" in recorded_payloads[1]["messages"][0]["content"]
        assert "紧急生成指引" in recorded_payloads[1]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_agenerate_token_escalation():
    llm = OpenAILLM(max_tokens=8192, max_retries=2, retry_delay=0.01)

    fail_resp = MagicMock()
    fail_resp.status_code = 200
    fail_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "",
                "reasoning_content": "Long thoughts...",
            },
            "finish_reason": "length",
        }],
        "usage": {"total_tokens": 8192},
    }

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": "异步成功生成的正文。",
            },
            "finish_reason": "stop",
        }],
        "usage": {"total_tokens": 4000},
    }

    recorded_payloads = []

    async def mock_post(url, headers, json):
        recorded_payloads.append(json)
        if len(recorded_payloads) == 1:
            return fail_resp
        return success_resp

    with patch.object(llm, "_get_async_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_get_client.return_value = mock_client

        result = await llm.agenerate("writer", "请写场景正文")

        assert result == "异步成功生成的正文。"
        assert len(recorded_payloads) == 2
        assert recorded_payloads[0]["max_tokens"] == 8192
        assert recorded_payloads[1]["max_tokens"] == 16384


@pytest.mark.asyncio
async def test_scene_generation_reuse_and_serial_fallback(tmp_path: Path):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir(parents=True)
    chapter_dir = tmp_path / "chapter_001"
    chapter_dir.mkdir(parents=True)

    # Pre-populate scene_001-01.txt with existing content
    (scenes_dir / "scene_001-01.txt").write_text("已有完整场景内容" * 20, encoding="utf-8")

    orchestrator = MagicMock()
    phase = GenerationPhase(orchestrator)

    ctx = ChapterContext(
        chapter_id="001",
        chapter_goal="测试目标",
        chapter_dir=chapter_dir,
        scenes_dir=scenes_dir,
        reports_dir=tmp_path / "reports",
        plan={
            "scenes": [
                {"scene_id": "001-01"},
                {"scene_id": "001-02"},
            ]
        },
    )

    call_count = {"001-02": 0}

    async def mock_agenerate(goal, c_dir, s_dir, scene, plan=None):
        sid = scene.get("scene_id")
        if sid == "001-02":
            call_count["001-02"] += 1
            if call_count["001-02"] == 1:
                # First parallel attempt fails
                raise RuntimeError("Parallel attempt failed due to concurrency")
            # Serial retry succeeds and creates the file
            (s_dir / f"scene_{sid}.txt").write_text("场景001-02成功生成", encoding="utf-8")

    with patch.object(phase, "_agenerate_scene", side_effect=mock_agenerate) as mock_gen:
        await phase._arun_scene_generation(ctx)

        # Scene 001-01 was reused, never called _agenerate_scene
        # Scene 001-02 failed once in parallel, then retried serially and succeeded
        assert call_count["001-02"] == 2
        assert (scenes_dir / "scene_001-02.txt").read_text(encoding="utf-8") == "场景001-02成功生成"
