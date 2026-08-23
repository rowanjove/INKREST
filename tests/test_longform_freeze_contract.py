from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def test_freeze_snapshot_records_worktree_and_flag_contract(tmp_path: Path) -> None:
    output = tmp_path / "freeze.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "capture_longform_freeze.py"),
            "--output",
            str(output),
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "benchmarks" / "longform" / "freeze.schema.json").read_text(
            encoding="utf-8"
        )
    )
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert not errors, "; ".join(error.message for error in errors)
    assert payload["commit"]
    assert payload["dirty"] is True
    assert payload["longform_flags"]["m1_catalog_pagination"] is True
