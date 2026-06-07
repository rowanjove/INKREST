"""Perf guardrails: bundle budget + API latency baseline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_bundle_budget_with_built_dist() -> None:
    dist = ROOT / "web" / "frontend" / "dist"
    if not (dist / "assets").is_dir():
        return
    from scripts.check_frontend_bundle import check_bundle

    issues = check_bundle(dist, ROOT / "benchmarks" / "frontend_bundle_budget.json")
    assert issues == [], "\n".join(issues)


def test_api_perf_within_baseline() -> None:
    from scripts.perf_api_baseline import check_baseline

    ok, _p95, issues = check_baseline(ROOT / "benchmarks" / "api_perf_baseline.json")
    assert ok, "\n".join(issues)