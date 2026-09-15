"""Tests for HWE CLI commands (PRD §63)."""

import json
import subprocess
import sys
from pathlib import Path


def test_cli_hwe_scan_json():
    text = "这不是一次普通的谈话，而是一场关乎生死存亡的残酷博弈。"
    res = subprocess.run(
        [sys.executable, "cli.py", "hwe-scan", "--text", text, "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "scores" in data
    assert "issues" in data
    assert any(i["hwe"]["rule_id"] == "HWE.STAGING.BINARY_CONTRAST" for i in data["issues"])


def test_cli_hwe_eval_assert_fpr():
    res = subprocess.run(
        [sys.executable, "cli.py", "hwe-eval", "--format", "json", "--assert-fpr"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "metrics" in data
    assert data["fpr_target_met"] is True
    assert data["metrics"]["false_positive_rate"] < 0.05


def test_cli_hwe_rebuild_memory_json():
    res = subprocess.run(
        [sys.executable, "cli.py", "hwe-rebuild-memory", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "total_chapters" in data
    assert "saturation_warning_count" in data
