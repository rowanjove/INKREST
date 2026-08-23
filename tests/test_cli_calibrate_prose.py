import argparse
import json
from pathlib import Path

import pytest

from cli import _normalize_argv, calibrate_prose_cmd
from novel_agent.quality.prose_identity import load_prose_identity_profile


def _args(root: Path, **overrides):
    values = {
        "root_dir": str(root),
        "root": None,
        "sample": [],
        "accepted_chapter": [],
        "output": None,
        "force": False,
        "list_versions": False,
        "restore_revision": None,
        "json_output": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_calibrate_prose_cli_reads_only_explicit_inputs_and_writes_profile(tmp_path: Path, capsys):
    sample = tmp_path / "sample.txt"
    chapter = tmp_path / "chapter_001.txt"
    sample.write_text("短句。雨停了。", encoding="utf-8")
    chapter.write_text("门开了。她没有进去。", encoding="utf-8")

    calibrate_prose_cmd(
        _args(
            tmp_path,
            sample=["sample.txt"],
            accepted_chapter=["chapter_001.txt"],
        )
    )

    output = json.loads(capsys.readouterr().out)
    assert output["sample_count"] == 2
    profile = load_prose_identity_profile(tmp_path)
    assert profile is not None
    assert {source["kind"] for source in profile["sources"]} == {"user_sample", "accepted_chapter"}


def test_calibrate_prose_cli_refuses_overwrite_without_force(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("一句话。", encoding="utf-8")
    calibrate_prose_cmd(_args(tmp_path, sample=["sample.txt"]))
    with pytest.raises(SystemExit) as exc_info:
        calibrate_prose_cmd(_args(tmp_path, sample=["sample.txt"]))
    assert exc_info.value.code == 2


def test_calibrate_prose_cli_requires_an_explicit_input(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        calibrate_prose_cmd(_args(tmp_path))
    assert exc_info.value.code == 2


def test_calibrate_prose_cli_lists_and_restores_revisions(tmp_path: Path, capsys):
    sample = tmp_path / "sample.txt"
    sample.write_text("一句话。", encoding="utf-8")
    calibrate_prose_cmd(_args(tmp_path, sample=["sample.txt"]))
    sample.write_text("第二版。", encoding="utf-8")
    calibrate_prose_cmd(_args(tmp_path, sample=["sample.txt"], force=True))
    capsys.readouterr()

    calibrate_prose_cmd(_args(tmp_path, list_versions=True))
    listed = json.loads(capsys.readouterr().out)
    assert [item["revision"] for item in listed["versions"]] == [2, 1]

    calibrate_prose_cmd(_args(tmp_path, restore_revision=1))
    restored = json.loads(capsys.readouterr().out)
    assert restored["restored_revision"] == 1
    assert load_prose_identity_profile(tmp_path)["revision"] == 3


def test_cli_normalizes_calibrate_prose_as_a_known_command():
    assert _normalize_argv(["calibrate-prose", "--sample", "sample.txt"])[0] == "calibrate-prose"
