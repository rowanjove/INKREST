from pathlib import Path

from novel_agent.services.batch_retry_queue import record_batch_retry
from unittest.mock import patch

from novel_agent.services.pipeline_pending import (
    collect_pipeline_alerts,
    count_pipeline_alerts,
    count_pipeline_alerts_cached,
    invalidate_pipeline_alerts_cache,
    summarize_pipeline_pending,
)
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


def test_collect_pipeline_alerts_matches_retry_and_gate(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    record_batch_retry(tmp_path, chapter_id="005", message="skip")
    d = tmp_path / "workspace" / "chapters" / "chapter_003"
    d.mkdir(parents=True)
    (d / "checkpoint.json").write_text(
        '{"chapter_id":"003","last_stage":"quality_blocked"}',
        encoding="utf-8",
    )
    alerts = collect_pipeline_alerts(tmp_path)
    assert count_pipeline_alerts(tmp_path) == 2
    stages = {a["last_stage"] for a in alerts}
    assert "batch_retry" in stages
    assert "quality_blocked" in stages
    assert summarize_pipeline_pending(tmp_path)["pending_total"] == count_pipeline_alerts(tmp_path)


def test_count_pipeline_alerts_cached_reuses_file(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    record_batch_retry(tmp_path, chapter_id="005", message="skip")
    expected = count_pipeline_alerts_cached(tmp_path)
    cache_path = tmp_path / "workspace" / "reports" / "pending_alert_count.cache.json"
    assert cache_path.is_file()
    with patch(
        "novel_agent.services.pipeline_pending.count_pipeline_alerts",
        side_effect=AssertionError("should not recompute"),
    ):
        assert count_pipeline_alerts_cached(tmp_path) == expected


def test_invalidate_pipeline_alerts_cache_forces_recompute(tmp_path: Path) -> None:
    _seed_ready(tmp_path)
    count_pipeline_alerts_cached(tmp_path)
    invalidate_pipeline_alerts_cache(tmp_path)
    cache_path = tmp_path / "workspace" / "reports" / "pending_alert_count.cache.json"
    assert not cache_path.is_file()