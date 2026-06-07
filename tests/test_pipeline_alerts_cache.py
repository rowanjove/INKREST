"""Pipeline alerts list cache."""

from pathlib import Path

from novel_agent.services.pipeline_pending import (
    collect_pipeline_alerts,
    collect_pipeline_alerts_cached,
    invalidate_pipeline_alerts_cache,
)
from tests.helpers.seed_engine import seed_usable_daily_model


def _seed_minimal(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "workspace").mkdir(exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text("llm:\n  daily_model_id: t\n", encoding="utf-8")
    seed_usable_daily_model(root, model_id="t")


def test_pipeline_alerts_cached_matches_uncached(tmp_path: Path) -> None:
    _seed_minimal(tmp_path)
    invalidate_pipeline_alerts_cache(tmp_path)
    direct = collect_pipeline_alerts(tmp_path)
    cached = collect_pipeline_alerts_cached(tmp_path)
    assert cached == direct
    cache_file = tmp_path / "workspace" / "reports" / "pipeline_alerts.cache.json"
    assert cache_file.is_file()