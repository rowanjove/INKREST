"""Longform benchmark scripts write schema-valid JSON without calling an LLM."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "benchmarks" / "longform" / "baseline.schema.json").read_text(
        encoding="utf-8"
    )
)


def _assert_schema(payload: dict) -> None:
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(payload), key=str)
    assert not errors, "; ".join(error.message for error in errors)
    assert payload["python"].split(".")[:2] in (["3", "11"], ["3", "12"])
    assert payload["llm_called"] is False
    assert isinstance(payload["elapsed_ms"], (int, float))
    assert payload["operation_elapsed_ms"] >= 0
    assert payload["peak_tracemalloc_bytes"] >= 0
    assert payload["repeat"] >= 1
    assert len(payload["latency_samples_ms"]) == payload["repeat"]
    assert payload["p95_elapsed_ms"] >= 0
    assert payload["p50_elapsed_ms"] >= 0
    assert payload["peak_rss_bytes"] >= 0


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def test_state_benchmark_emits_valid_json(tmp_path: Path) -> None:
    output = tmp_path / "bench-state.json"
    result = _run(
        "benchmark_longform_state.py",
        "--chapters",
        "20",
        "--seed",
        "1",
        "--output",
        str(output),
        "--workdir",
        str(tmp_path / "project"),
        "--repeat",
        "3",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    _assert_schema(payload)
    assert payload["kind"] == "state"
    assert payload["chapters"] == 20
    assert payload["llm_called"] is False
    assert payload["queries"]["catalog_page"]["ok"] is True
    assert payload["queries"]["max_chapter"]["value"] == 20
    assert "events" in payload["queries"]
    assert "open_threads" in payload["queries"]
    assert "character_state" in payload["queries"]
    assert "publication_summary" in payload["queries"]
    assert "backup_inventory" in payload["queries"]
    assert not (ROOT / "projects").joinpath("bench-state.json").exists()


def test_export_benchmark_streams_txt(tmp_path: Path) -> None:
    output = tmp_path / "bench-export.json"
    result = _run(
        "benchmark_longform_export.py",
        "--chapters",
        "12",
        "--format",
        "txt",
        "--output",
        str(output),
        "--workdir",
        str(tmp_path / "export-project"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    _assert_schema(payload)
    assert payload["kind"] == "export"
    assert payload["format"] == "txt"
    assert payload["llm_called"] is False
    assert payload["streamed"] is True
    assert payload["chapter_count"] == 12
