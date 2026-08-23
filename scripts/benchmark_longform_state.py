#!/usr/bin/env python3
"""Measure SQLite catalog/state queries on a synthetic longform project."""

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

from novel_agent.services.longform_synth import seed_synthetic_project
from novel_agent.services.v2_reset import list_backup_inventory
from novel_agent.state.sqlite_store import SQLiteStateStore
from benchmark_longform_lib import (
    add_common_args,
    assert_supported_python,
    finish_memory_measurement,
    machine_info,
    percentile95,
    percentile50,
    prepare_workdir,
    timed,
    validate_repeat,
    write_json,
    start_memory_measurement,
)


def main() -> int:
    assert_supported_python()
    parser = argparse.ArgumentParser()
    add_common_args(parser)
    args = parser.parse_args()
    repeat = validate_repeat(args.repeat)
    workdir = prepare_workdir(args)
    started = time.perf_counter()
    seed_synthetic_project(workdir, chapters=int(args.chapters), seed=int(args.seed))
    memory_started = start_memory_measurement()
    store = SQLiteStateStore(workdir)
    def run_queries() -> dict:
        return {
            "catalog_page": timed(
                lambda: store.list_manuscript_document_summaries_page(offset=0, limit=100)
            ),
            "max_chapter": timed(store.max_numeric_chapter_id),
            "events": timed(lambda: store.list_events(limit=20)),
            "open_threads": timed(store.list_threads),
            "character_state": timed(store.list_characters),
            "publication_summary": timed(
                lambda: {
                    "count": store.count_manuscript_document_summaries(has_content=True),
                    "words": store.sum_manuscript_word_count(has_content=True),
                }
            ),
            "backup_inventory": timed(lambda: list_backup_inventory(workdir)),
        }

    latency_samples: list[float] = []
    queries = {}
    for _ in range(repeat):
        sample_started = time.perf_counter()
        queries = run_queries()
        latency_samples.append((time.perf_counter() - sample_started) * 1000)
    memory = finish_memory_measurement(memory_started)
    payload = {
        "kind": "state",
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
        "queries": queries,
    }
    queries["catalog_page"]["value"] = len(queries["catalog_page"]["value"])
    write_json(Path(args.output), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
