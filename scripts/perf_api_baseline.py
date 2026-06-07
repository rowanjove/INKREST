#!/usr/bin/env python3
"""Measure hot API latencies against benchmarks/api_perf_baseline.json."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "benchmarks" / "api_perf_baseline.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _seed_project(root: Path) -> None:
    from tests.helpers.seed_engine import seed_usable_daily_model

    for rel in (
        "workspace",
        "config",
        "workspace/chapters",
        "workspace/reports",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "config" / "pipeline.yaml").write_text(
        "llm:\n  daily_model_id: t\n", encoding="utf-8"
    )
    (root / "workspace" / "outline.json").write_text(
        json.dumps({"target_chapters": 20, "scale_profile": {"scale": "short"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    seed_usable_daily_model(root, model_id="t")


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def measure_endpoints(
    endpoints: Dict[str, int],
    *,
    iterations: int,
) -> Tuple[Dict[str, float], List[str]]:
    from fastapi.testclient import TestClient

    import web.server as web_server
    from web.server import app as web_app

    tmpdir = Path(tempfile.mkdtemp(prefix="novel-perf-api-"))
    _seed_project(tmpdir)

    original_base = web_server.BASE_DIR
    original_active = web_server._active_project_id
    timings: Dict[str, List[float]] = {path: [] for path in endpoints}
    errors: List[str] = []

    try:
        web_server.BASE_DIR = tmpdir
        web_server._active_project_id = None
        client = TestClient(web_app)

        for _ in range(max(1, iterations)):
            for path in endpoints:
                start = time.perf_counter()
                resp = client.get(path)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                if resp.status_code >= 400:
                    errors.append(f"{path} returned {resp.status_code}")
                timings[path].append(elapsed_ms)
    finally:
        web_server.BASE_DIR = original_base
        web_server._active_project_id = original_active
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)

    p95 = {path: _percentile(values, 95) for path, values in timings.items()}
    return p95, errors


def check_baseline(baseline_path: Path) -> Tuple[bool, Dict[str, float], List[str]]:
    spec = json.loads(baseline_path.read_text(encoding="utf-8"))
    endpoints = spec.get("endpoints") or {}
    if not isinstance(endpoints, dict):
        raise ValueError("baseline endpoints must be an object")
    iterations = int(spec.get("iterations") or 5)
    p95, errors = measure_endpoints(endpoints, iterations=iterations)

    violations: List[str] = []
    for path, limit in endpoints.items():
        limit_ms = float(limit)
        actual = p95.get(path, 0.0)
        if actual > limit_ms:
            violations.append(f"{path} p95={actual:.1f}ms > {limit_ms:.0f}ms")

    ok = not violations and not errors
    return ok, p95, violations + errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="JSON baseline file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when any endpoint exceeds baseline (default)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print measured p95 timings as JSON",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    if not baseline_path.is_file():
        print(f"Missing baseline: {baseline_path}", file=sys.stderr)
        return 2

    ok, p95, issues = check_baseline(baseline_path)
    if args.report or not args.check:
        print(json.dumps({"p95_ms": p95, "ok": ok}, ensure_ascii=False, indent=2))

    if issues:
        print("API perf baseline issues:", file=sys.stderr)
        for item in issues:
            print(f"  - {item}", file=sys.stderr)

    if args.check and not ok:
        return 1
    if ok:
        print("OK: API p95 within baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())