"""Structured error code classification."""

import unittest

from novel_agent.errors import ErrorCode, classify_exception, failure_payload, http_error_detail
from novel_agent.exceptions import FatalPipelineError, LLMAuthError, TaskAbortedError
from novel_agent.pipeline import assert_llm_ready, llm_config_error
from tests.helpers.seed_engine import seed_usable_daily_model


class ErrorCodeTests(unittest.TestCase):
    def test_classify_fatal_pipeline_llm(self):
        code, hint = classify_exception(
            FatalPipelineError("日常模型未配置或仍为 Static 占位")
        )
        self.assertEqual(code, ErrorCode.LLM_NOT_READY)
        self.assertIn("模型", hint)

    def test_classify_batch_running(self):
        code, _ = classify_exception(ValueError("Novel batch already running (task x)"))
        self.assertEqual(code, ErrorCode.NOVEL_BATCH_RUNNING)

    def test_failure_payload_shape(self):
        payload = failure_payload(LLMAuthError("bad key"))
        self.assertEqual(payload["code"], "LLM_AUTH")
        self.assertIn("failure_hint", payload)

    def test_http_error_detail_dict(self):
        body = http_error_detail(ErrorCode.ARC_QUEUE_STALE)
        self.assertEqual(body["code"], "ARC_QUEUE_STALE")
        self.assertIn("detail", body)

    def test_llm_ready_after_seed(self):
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="novel-llm-ready-"))
        try:
            (tmp / "config").mkdir()
            (tmp / "config" / "pipeline.yaml").write_text(
                "llm:\n  daily_model_id: t1\n", encoding="utf-8"
            )
            seed_usable_daily_model(tmp, model_id="t1")
            self.assertIsNone(llm_config_error(tmp))
            assert_llm_ready(tmp)
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()