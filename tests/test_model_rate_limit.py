import os
from unittest.mock import patch

import pytest

from novel_agent.control.model_rate_limit import (
    MAX_REMOTE_CALLS,
    enforce_model_call_rate_limit,
    reset_model_call_rate_limit,
)
from novel_agent.exceptions import LLMRateLimitError


def test_local_serving_does_not_rate_limit_model_calls():
    reset_model_call_rate_limit()
    with patch.dict(os.environ, {"NOVEL_AGENT_ALLOW_REMOTE": ""}, clear=False):
        os.environ.pop("NOVEL_AGENT_ALLOW_REMOTE", None)
        for _ in range(MAX_REMOTE_CALLS + 5):
            enforce_model_call_rate_limit()


def test_remote_serving_caps_model_calls():
    reset_model_call_rate_limit()
    with patch.dict(os.environ, {"NOVEL_AGENT_ALLOW_REMOTE": "1"}):
        for _ in range(MAX_REMOTE_CALLS):
            enforce_model_call_rate_limit(now=1000.0)
        with pytest.raises(LLMRateLimitError):
            enforce_model_call_rate_limit(now=1000.0)


def test_remote_rate_limit_can_be_configured_for_longform_workloads():
    reset_model_call_rate_limit()
    with patch.dict(
        os.environ,
        {
            "NOVEL_AGENT_ALLOW_REMOTE": "1",
            "NOVEL_AGENT_MAX_MODEL_CALLS_PER_MINUTE": "64",
        },
    ):
        for _ in range(64):
            enforce_model_call_rate_limit(now=2000.0)
        with pytest.raises(LLMRateLimitError, match="64/60s"):
            enforce_model_call_rate_limit(now=2000.0)
