"""Materialized progress snapshot on disk."""

from pathlib import Path

from novel_agent.services.progress_summary import (
    build_progress_summary,
    invalidate_progress_summary_cache,
    load_progress_snapshot_stats,
)
from tests.helpers.seed_engine import seed_usable_daily_model


def _seed_minimal(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "workspace").mkdir(exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text("llm:\n  daily_model_id: t\n", encoding="utf-8")
    seed_usable_daily_model(root, model_id="t")


def test_progress_snapshot_written_and_invalidated(tmp_path: Path) -> None:
    _seed_minimal(tmp_path)
    summary = build_progress_summary(tmp_path)
    snapshot = load_progress_snapshot_stats(tmp_path)
    assert snapshot is not None
    assert snapshot["library_indexed"] == summary["library_indexed"]
    assert snapshot["total_words"] == summary["total_words"]
    assert (tmp_path / "workspace" / "reports" / "progress_snapshot.json").is_file()

    invalidate_progress_summary_cache(tmp_path)
    assert load_progress_snapshot_stats(tmp_path) is None