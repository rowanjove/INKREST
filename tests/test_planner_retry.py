"""Regression tests for bounded planner JSON retries."""

import asyncio
import json

import pytest

from novel_agent.agents.planner import PlannerAgent
from novel_agent.exceptions import LLMResponseError


class SequencedLLM:
    """Return one response per call so malformed-then-valid flows are testable."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, role: str, prompt: str) -> str:
        assert role == "planner"
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("planner called more times than expected")
        return self.responses.pop(0)

    async def agenerate(self, role: str, prompt: str) -> str:
        return self.generate(role, prompt)


def _valid_plan() -> str:
    return json.dumps(
        {
            "chapter_id": "001",
            "chapter_title": "雨夜",
            "scenes": [{"scene_id": "001-01", "purpose": "开场"}],
        },
        ensure_ascii=False,
    )


def test_planner_retries_once_after_truncated_json() -> None:
    llm = SequencedLLM(['{"scenes":[{"scene_id":"001-01","purpose":"未完'])
    llm.responses.append(_valid_plan())

    plan = PlannerAgent(llm).create_plan("001", "雨夜开场")

    assert plan["chapter_id"] == "001"
    assert len(llm.prompts) == 2
    assert "JSON 格式重试" in llm.prompts[1]
    assert "场景不超过 12 个" in llm.prompts[1]


def test_planner_async_retries_once_after_truncated_json() -> None:
    llm = SequencedLLM(['{"scenes":[{"scene_id":"001-01","purpose":"未完'])
    llm.responses.append(_valid_plan())

    plan = asyncio.run(PlannerAgent(llm).acreate_plan("001", "雨夜开场"))

    assert plan["scenes"][0]["scene_id"] == "001-01"
    assert len(llm.prompts) == 2


def test_planner_reports_bounded_retry_failure() -> None:
    llm = SequencedLLM(["不是 JSON", "仍然不是 JSON"])

    with pytest.raises(LLMResponseError, match="自动重试仍失败"):
        PlannerAgent(llm).create_plan("001", "雨夜开场")

    assert len(llm.prompts) == 2
