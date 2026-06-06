from pathlib import Path

from novel_agent.services.batch_retry_queue import record_batch_retry
from novel_agent.services.pipeline_pending import summarize_pipeline_pending
from tests.test_full_chain_chaos import _seed_ready


def test_summarize_counts_retry_and_gate(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    record_batch_retry(tmp_path, chapter_id="005", message="skip")
    d = tmp_path / "workspace" / "chapters" / "chapter_003"
    d.mkdir(parents=True)
    (d / "checkpoint.json").write_text(
        '{"chapter_id":"003","last_stage":"quality_blocked"}',
        encoding="utf-8",
    )
    summary = summarize_pipeline_pending(tmp_path)
    assert summary["pending_retry_count"] == 1
    assert summary["pending_gate_count"] == 1
    assert summary["pending_total"] == 2