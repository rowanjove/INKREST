import json
import subprocess
import sys
from pathlib import Path

from novel_agent.services.vector_rebuild import load_vector_rebuild_checkpoint, save_vector_rebuild_checkpoint


def test_vector_rebuild_checkpoint_is_atomic_and_resumable(tmp_path: Path):
    first = save_vector_rebuild_checkpoint(
        tmp_path, last_chapter_id="005", last_chunk_id="chunk-9", processed_rows=9, backend="sqlite"
    )
    assert first["completed"] is False
    assert load_vector_rebuild_checkpoint(tmp_path)["last_chunk_id"] == "chunk-9"
    done = save_vector_rebuild_checkpoint(
        tmp_path, last_chapter_id="005", last_chunk_id="chunk-9", processed_rows=9, completed=True, backend="sqlite"
    )
    assert done["completed"] is True
    assert load_vector_rebuild_checkpoint(tmp_path)["completed"] is True


def test_chaos_runner_records_fault_without_model_calls(tmp_path: Path):
    report = tmp_path / "chaos.json"
    result = subprocess.run(
        [sys.executable, "scripts/chaos_long_run.py", "--chapters", "1", "--fault", "vector-rebuild", "--abort-after", "1", "--report", str(report)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["model_calls"] == 0
    assert payload["fault"] == "vector-rebuild"
    assert payload["recovery"]["unique_final_chapters"] is True
