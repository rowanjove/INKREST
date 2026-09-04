from __future__ import annotations

import asyncio
import io
import json
import pickle
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from novel_agent.agents.base import OpenAILLM
from novel_agent.exceptions import LLMResponseError
from novel_agent.domain.stat_fsm import RealmLadder
from novel_agent.pipeline import PipelineConfig
from novel_agent.plugins.sandbox import _RestrictedUnpickler
from novel_agent.quality.punct_cleaner import clean_punctuation_and_typography
from novel_agent.state.sqlite_schema import db_write_lock


def test_db_write_lock_reentrancy(tmp_path: Path):
    """Verify @db_write_lock is reentrant and does not deadlock when called from within the worker thread."""
    db_file = tmp_path / "test.sqlite"

    class DummyStore:
        def __init__(self, path: Path):
            self.db_path = path

        @db_write_lock
        def outer(self, val: int) -> int:
            return self.inner(val + 1)

        @db_write_lock
        def inner(self, val: int) -> int:
            return val * 2

    store = DummyStore(db_file)
    result = store.outer(5)
    # outer(5) -> inner(6) -> 12
    assert result == 12


def test_pipeline_get_call_log_deduplication():
    """Verify get_call_log() deduplicates shared LLMClient instances."""
    client = MagicMock()
    client.call_log = [
        {"role": "writer", "tokens": 100},
        {"role": "stitch", "tokens": 150},
    ]

    cfg = PipelineConfig(
        root_dir=Path("."),
        llm=client,
        llm_registry={
            "default": client,
            "writer": client,
            "stitch_editor": client,
            "style_editor": client,
        },
    )

    logs = cfg.get_call_log()
    # Must only contain the 2 entries once, not 2 * 4 = 8 entries!
    assert len(logs) == 2
    assert logs == client.call_log


def test_punct_cleaner_preserves_fullwidth_indentation():
    """Verify clean_punctuation_and_typography preserves first line full-width indentation."""
    raw_text = "　　第一章 故事开始。\n\n　　第二段 接着展开……"
    cleaned = clean_punctuation_and_typography(raw_text)

    lines = cleaned.split("\n")
    # First paragraph must preserve \u3000\u3000
    assert lines[0].startswith("　　第一章")
    # Second paragraph must also preserve \u3000\u3000
    assert any(line.startswith("　　第二段") for line in lines)


def test_realm_ladder_normalized_matching():
    """Verify RealmLadder accurately matches variants with '期' and handles edge cases safely."""
    ladder = RealmLadder()

    # Exact match
    assert ladder.index_of("金丹初期") is not None

    # Normalized match with '期'
    assert ladder.index_of("金丹期初期") == ladder.index_of("金丹初期")
    assert ladder.index_of("元婴期圆满") == ladder.index_of("元婴圆满")

    # Short invalid words must not collide
    assert ladder.index_of("期") is None
    assert ladder.index_of("a") is None
    assert ladder.index_of("") is None


def test_openai_llm_call_log_management():
    """Verify OpenAILLM limits call_log size and provides clear_call_log()."""
    llm = OpenAILLM()
    llm.call_log = [{"i": i} for i in range(1200)]
    assert len(llm.call_log) == 1200

    llm.clear_call_log()
    assert len(llm.call_log) == 0


def test_restricted_unpickler_blocks_dangerous_globals():
    """Verify _RestrictedUnpickler blocks unpickling objects from untrusted modules."""
    import os

    class Exploit:
        def __reduce__(self):
            return (os.system, ("echo hacked",))

    dangerous_blob = pickle.dumps(Exploit())

    unpickler = _RestrictedUnpickler(io.BytesIO(dangerous_blob))
    with pytest.raises(pickle.UnpicklingError) as exc_info:
        unpickler.load()

    assert "forbidden in sandbox" in str(exc_info.value)


def test_openai_stream_does_not_append_full_fallback_after_partial_output():
    class InterruptedResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield "data: " + json.dumps(
                {"choices": [{"delta": {"content": "开头"}}]},
                ensure_ascii=False,
            )
            raise OSError("connection reset")

    class InterruptedClient:
        def stream(self, *_args, **_kwargs):
            return InterruptedResponse()

    async def exercise():
        llm = OpenAILLM(base_url="https://api.openai.com/v1")
        llm._get_async_client = lambda: InterruptedClient()

        async def full_fallback(*_args, **_kwargs):
            return "开头和完整结尾"

        llm.agenerate = full_fallback
        chunks = []
        with pytest.raises(OSError, match="connection reset"):
            async for chunk in llm.astream("assistant", "prompt"):
                chunks.append(chunk)
        return chunks

    assert asyncio.run(exercise()) == ["开头"]


def test_openai_stream_raises_when_only_malformed_sse():
    class BadResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield "data: {not-json"
            yield "data: [DONE]"

    class BadClient:
        def stream(self, *_args, **_kwargs):
            return BadResponse()

    async def exercise():
        llm = OpenAILLM(base_url="https://api.openai.com/v1")
        llm._get_async_client = lambda: BadClient()
        chunks = []
        async for chunk in llm.astream("assistant", "prompt"):
            chunks.append(chunk)
        return chunks

    with pytest.raises(LLMResponseError, match="malformed SSE"):
        asyncio.run(exercise())
