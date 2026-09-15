"""Optional real-LLM smoke (skipped unless NOVEL_AGENT_LLM_SMOKE=1)."""

import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

import pytest

from tests.helpers.seed_engine import seed_usable_daily_model


@pytest.mark.skipif(
    os.environ.get("NOVEL_AGENT_LLM_SMOKE", "").lower() not in ("1", "true", "yes"),
    reason=(
        "Set NOVEL_AGENT_LLM_SMOKE=1, NOVEL_AGENT_SMOKE_MODEL and a smoke API key "
        "(unless the endpoint is loopback) to run"
    ),
)
class LlmOneChapterSmoke(unittest.TestCase):
    def test_one_chapter_generates_text(self):
        model_name = os.environ.get("NOVEL_AGENT_SMOKE_MODEL", "").strip()
        if not model_name:
            self.skipTest("NOVEL_AGENT_SMOKE_MODEL not set")
        provider = os.environ.get("NOVEL_AGENT_SMOKE_PROVIDER", "openai").strip()
        base_url = os.environ.get("NOVEL_AGENT_SMOKE_BASE_URL", "").strip()
        api_key = (
            os.environ.get("NOVEL_AGENT_SMOKE_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        host = urlparse(base_url).hostname if base_url else ""
        is_loopback = host in {"localhost", "127.0.0.1", "::1"}
        if not api_key and not is_loopback:
            self.skipTest("NOVEL_AGENT_SMOKE_API_KEY or OPENAI_API_KEY not set")
        api_key = api_key or "local-smoke"

        tmp = Path(tempfile.mkdtemp(prefix="novel-llm-smoke-"))
        try:
            from web.helpers import _ensure_dirs

            _ensure_dirs(tmp)
            model_id = "llm-smoke"
            (tmp / "config" / "pipeline.yaml").write_text(
                f"llm:\n  daily_model_id: {model_id}\nruntime:\n  max_workers: 1\n",
                encoding="utf-8",
            )
            seed_usable_daily_model(
                tmp,
                model_id=model_id,
                provider=provider,
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )

            from novel_agent.orchestrator import NovelOrchestrator
            from novel_agent.pipeline import PipelineConfig

            config = PipelineConfig.from_config(tmp)
            orch = NovelOrchestrator(config)
            result = orch.run_chapter("001", "主角登场，建立世界观。")
            text = (
                tmp
                / "workspace"
                / "chapters"
                / "chapter_001"
                / "chapter_final.txt"
            ).read_text(encoding="utf-8")
            self.assertTrue(len(text) > 200, f"chapter too short: {len(text)}")
            self.assertEqual(result.chapter_id, "001")
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)
