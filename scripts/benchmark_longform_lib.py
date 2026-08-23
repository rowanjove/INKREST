"""Shared helpers for longform benchmark commands."""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
import time
import tracemalloc
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CHAPTERS = {100, 500, 1000, 3000, 5000}


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chapters", type=int, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, default=None)
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the measured operation to produce a stable P95 latency.",
    )


def assert_supported_python() -> None:
    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        raise SystemExit("Longform benchmarks require Python 3.11 or 3.12")


def start_memory_measurement() -> float:
    tracemalloc.start()
    return time.perf_counter()


def finish_memory_measurement(started: float) -> Dict[str, Any]:
    current, peak = tracemalloc.get_traced_memory()
    rss = process_peak_rss_bytes()
    tracemalloc.stop()
    return {
        "operation_elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "peak_tracemalloc_bytes": int(peak),
        "current_tracemalloc_bytes": int(current),
        "peak_rss_bytes": int(rss),
    }


def machine_info() -> Dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
        "commit": git_commit(),
    }


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except OSError:
        pass
    return "unknown"


def process_peak_rss_bytes() -> int:
    """Return process peak RSS without adding a mandatory runtime dependency."""

    if os.name == "nt":
        class _Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("page_fault_count", ctypes.c_ulong),
                ("peak_working_set_size", ctypes.c_size_t),
                ("working_set_size", ctypes.c_size_t),
                ("quota_peak_paged_pool_usage", ctypes.c_size_t),
                ("quota_paged_pool_usage", ctypes.c_size_t),
                ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
                ("quota_non_paged_pool_usage", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t),
                ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        counters = _Counters()
        counters.cb = ctypes.sizeof(_Counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        api = ctypes.WinDLL("Psapi.dll", use_last_error=True)
        get_memory_info = api.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_Counters),
            ctypes.c_ulong,
        ]
        get_memory_info.restype = ctypes.c_int
        ok = get_memory_info(
            process,
            ctypes.byref(counters),
            counters.cb,
        )
        if ok:
            return int(counters.peak_working_set_size)
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value * (1024 if sys.platform != "darwin" else 1)
    except (ImportError, AttributeError, OSError):
        return 0


def timed(fn: Callable[[], Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    value = fn()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {"ok": True, "elapsed_ms": round(elapsed_ms, 3), "value": value}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    if "projects" in path.resolve().parts and path.resolve().is_relative_to(ROOT / "projects"):
        raise SystemExit("Refusing to write benchmark output into projects/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_workdir(args: argparse.Namespace) -> Path:
    chapters = int(args.chapters)
    if chapters not in ALLOWED_CHAPTERS and chapters < 100:
        # Contract tests use small chapter counts.
        if chapters < 1:
            raise SystemExit("--chapters must be >= 1")
    workdir = Path(args.workdir) if args.workdir else Path(args.output).parent / "longform-bench-work"
    if workdir.resolve().is_relative_to(ROOT / "projects"):
        raise SystemExit("Refusing to seed a synthetic project inside projects/")
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def validate_repeat(value: int) -> int:
    repeat = int(value)
    if repeat < 1 or repeat > 100:
        raise SystemExit("--repeat must be between 1 and 100")
    return repeat


def percentile95(samples_ms: list[float]) -> float:
    if not samples_ms:
        return 0.0
    ordered = sorted(float(sample) for sample in samples_ms)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
    return round(ordered[index], 3)


def percentile50(samples_ms: list[float]) -> float:
    if not samples_ms:
        return 0.0
    ordered = sorted(float(sample) for sample in samples_ms)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.50) - 1))
    return round(ordered[index], 3)
