"""Deterministic tests for the performance guardrail helpers."""

import json

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_bundle_budget_with_built_dist() -> None:
    dist = ROOT / "web" / "frontend" / "dist"
    if not (dist / "assets").is_dir():
        return
    from scripts.check_frontend_bundle import check_bundle

    issues = check_bundle(dist, ROOT / "benchmarks" / "frontend_bundle_budget.json")
    assert issues == [], "\n".join(issues)


def test_check_baseline_forwards_sampling_configuration(tmp_path, monkeypatch) -> None:
    from scripts import perf_api_baseline

    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "warmup_iterations": 3,
                "iterations": 20,
                "endpoints": {"/api/health": 50},
            }
        ),
        encoding="utf-8",
    )
    received = {}

    def fake_measure(endpoints, *, iterations, warmup_iterations):
        received.update(
            endpoints=endpoints,
            iterations=iterations,
            warmup_iterations=warmup_iterations,
        )
        return {"/api/health": 10.0}, []

    monkeypatch.setattr(perf_api_baseline, "measure_endpoints", fake_measure)

    ok, _p95, issues = perf_api_baseline.check_baseline(baseline)

    assert ok is True
    assert issues == []
    assert received == {
        "endpoints": {"/api/health": 50},
        "iterations": 20,
        "warmup_iterations": 3,
    }
