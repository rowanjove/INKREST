#!/usr/bin/env python3
"""Measure streaming TXT/Markdown export on a synthetic longform project."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from novel_agent.exporters.markdown_exporter import export_markdown
from novel_agent.exporters.txt_exporter import export_txt
from novel_agent.services.longform_synth import seed_synthetic_project
from benchmark_longform_lib import (
    add_common_args,
    assert_supported_python,
    finish_memory_measurement,
    machine_info,
    percentile95,
    percentile50,
    prepare_workdir,
    validate_repeat,
    write_json,
    start_memory_measurement,
)


def main() -> int:
    assert_supported_python()
    parser = argparse.ArgumentParser()
    add_common_args(parser)
    parser.add_argument("--format", choices=("txt", "markdown", "md"), default="txt")
    args = parser.parse_args()
    repeat = validate_repeat(args.repeat)
    workdir = prepare_workdir(args)
    started = time.perf_counter()
    seed_synthetic_project(workdir, chapters=int(args.chapters), seed=int(args.seed))
    memory_started = start_memory_measurement()
    fmt = "markdown" if args.format in {"markdown", "md"} else "txt"
    output_file = workdir / f"export.{ 'md' if fmt == 'markdown' else 'txt' }"
    latency_samples: list[float] = []
    for _ in range(repeat):
        sample_started = time.perf_counter()
        if fmt == "markdown":
            export_markdown(workdir, output_file, title="合成长篇")
        else:
            export_txt(workdir, output_file)
        latency_samples.append((time.perf_counter() - sample_started) * 1000)
    memory = finish_memory_measurement(memory_started)
    payload = {
        "kind": "export",
        "chapters": int(args.chapters),
        "seed": int(args.seed),
        "repeat": repeat,
        "python": sys.version.split()[0],
        "llm_called": False,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "setup_elapsed_ms": round((memory_started - started) * 1000, 3),
        **memory,
        "machine": machine_info(),
        "latency_samples_ms": [round(value, 3) for value in latency_samples],
        "p95_elapsed_ms": percentile95(latency_samples),
        "p50_elapsed_ms": percentile50(latency_samples),
        "format": fmt,
        "streamed": True,
        "chapter_count": int(args.chapters),
        "output_bytes": output_file.stat().st_size if output_file.is_file() else 0,
    }
    write_json(Path(args.output), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
