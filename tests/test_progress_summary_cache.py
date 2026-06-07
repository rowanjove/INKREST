"""Progress summary TTL cache."""

import time
from pathlib import Path

from novel_agent.services.progress_summary import (
    build_progress_summary,
    invalidate_progress_summary_cache,
)
from tests.helpers.seed_engine import seed_usable_daily_model


def _seed_minimal(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "workspace").mkdir(exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text("llm:\n  daily_model_id: t\n", encoding="utf-8")
    seed_usable_daily_model(root, model_id="t")


def test_progress_summary_cache_hit_within_ttl(tmp_path: Path) -> None:
    _seed_minimal(tmp_path)
    first = build_progress_summary(tmp_path)
    second = build_progress_summary(tmp_path)
    assert first == second
    invalidate_progress_summary_cache(tmp_path)
    third = build_progress_summary(tmp_path)
    assert third.keys() == first.keys()