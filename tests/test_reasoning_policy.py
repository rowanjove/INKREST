"""Tests for ReasoningPolicy, thinking payload contracts, and truncation error escalation."""

import json
import pytest
import httpx
from unittest.mock import MagicMock, patch

from novel_agent.agents.base import OpenAILLM, ReasoningPolicy
from novel_agent.exceptions import LLMThinkingTruncatedError, RetryExhaustedError


def test_reasoning_policy_role_defaults():
    # DeepSeek model: reasoning roles default to enabled
    p_planner = ReasoningPolicy.resolve("planner", "deepseek-v4")
    assert p_planner.thinking_enabled is True
    assert p_planner.strip_temperature is True

    p_editor = ReasoningPolicy.resolve("chief_editor", "deepseek-v4")
    assert p_editor.thinking_enabled is True

    # Creative / text generation roles default to disabled
    p_writer = ReasoningPolicy.resolve("writer", "deepseek-v4")
    assert p_writer.thinking_enabled is False
    assert p_writer.strip_temperature is False

    p_expander = ReasoningPolicy.resolve("expander", "deepseek-v4")
    assert p_expander.thinking_enabled is False

    p_style = ReasoningPolicy.resolve("style_editor", "deepseek-v4")
    assert p_style.thinking_enabled is False

    # Non-deepseek model defaults to disabled
    p_gpt = ReasoningPolicy.resolve("planner", "gpt-4o-mini")
    assert p_gpt.thinking_enabled is False


def test_reasoning_policy_explicit_override():
    # User explicitly disables thinking for a planner
    p_off = ReasoningPolicy.resolve("planner", "deepseek-v4", user_thinking=False)
    assert p_off.thinking_enabled is False

    # User explicitly enables thinking for a writer
    p_on = ReasoningPolicy.resolve("writer", "deepseek-v4", user_thinking=True)
    assert p_on.thinking_enabled is True


def test_openai_payload_contract_deepseek_thinking():
    # Writer role on DeepSeek: thinking disabled, temperature preserved
    llm_writer = OpenAILLM(model="deepseek-v4", api_key="sk-test", temperature=0.7)
    _url, _headers, payload_writer = llm_writer._build_payload("writer", "请写正文")
    assert payload_writer["thinking"] == {"type": "disabled"}
    assert payload_writer["temperature"] == 0.7

    # Planner role on DeepSeek: thinking enabled, temperature stripped, reasoning_effort passed
    llm_planner = OpenAILLM(model="deepseek-v4", api_key="sk-test", temperature=0.7)
    _url, _headers, payload_planner = llm_planner._build_payload("planner", "请生成大纲")
    assert payload_planner["thinking"] == {"type": "enabled"}
    assert payload_planner["reasoning_effort"] == "high"
    assert "temperature" not in payload_planner


def test_openai_payload_contract_non_deepseek():
    # Standard OpenAI model should not receive DeepSeek's thinking object
    llm_gpt = OpenAILLM(model="gpt-4o", api_key="sk-test", temperature=0.5)
    _url, _headers, payload_gpt = llm_gpt._build_payload("writer", "Write text")
    assert "thinking" not in payload_gpt
    assert payload_gpt["temperature"] == 0.5


def test_process_response_detects_thinking_truncation():
    llm = OpenAILLM(model="deepseek-v4", api_key="sk-test")
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "id": "chatcmpl-test1234",
        "model": "deepseek-v4",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",  # Empty content!
                    "reasoning_content": "Long detailed chain of thought " * 50,
                },
                "finish_reason": "length",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 4096,
            "total_tokens": 4196,
            "reasoning_tokens": 4096,
        },
    }

    with pytest.raises(LLMThinkingTruncatedError) as exc_info:
        llm._process_response(fake_response, "writer", 0.0)

    err = exc_info.value
    assert "思考过程超限截断" in str(err)
    assert err.role == "writer"
    assert err.finish_reason == "length"
    assert err.usage["reasoning_tokens"] == 4096


def test_generate_retry_escalation_on_thinking_truncation():
    llm = OpenAILLM(model="deepseek-v4", api_key="sk-test", max_retries=2, max_tokens=2048)

    # First attempt: truncated with reasoning
    resp1 = MagicMock(spec=httpx.Response)
    resp1.status_code = 200
    resp1.json.return_value = {
        "id": "cmpl-1",
        "model": "deepseek-v4",
        "choices": [
            {
                "message": {"content": "", "reasoning_content": "Thinking too much... " * 50},
                "finish_reason": "length",
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 2048, "total_tokens": 2098},
    }

    # Second attempt: succeeds with content
    resp2 = MagicMock(spec=httpx.Response)
    resp2.status_code = 200
    resp2.json.return_value = {
        "id": "cmpl-2",
        "model": "deepseek-v4",
        "choices": [
            {
                "message": {"content": "成功输出的第一章正文内容。"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 60, "completion_tokens": 500, "total_tokens": 560},
    }

    mock_client = MagicMock()
    mock_client.post.side_effect = [resp1, resp2]

    with patch.object(llm, "_get_client", return_value=mock_client):
        result = llm.generate("writer", "写第1章")
        assert result == "成功输出的第一章正文内容。"
        assert mock_client.post.call_count == 2
        second_call_payload = mock_client.post.call_args_list[1][1]["json"]
        assert second_call_payload["max_tokens"] >= 4096
        assert second_call_payload["thinking"] == {"type": "disabled"}
