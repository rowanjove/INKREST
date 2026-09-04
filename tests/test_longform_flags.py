import json
from pathlib import Path

from novel_agent.control.longform_flags import flag_enabled, longform_flags


def _write_scale(root: Path, scale: str) -> None:
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "outline.json").write_text(
        json.dumps({"scale_profile": {"scale": scale}}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_module_defaults_keep_memory_flags_off():
    flags = longform_flags(None)
    assert flags["m2_hybrid_retrieval"] is False
    assert flags["m3_canon_engine"] is False


def test_short_and_above_enable_memory_flags(tmp_path: Path):
    _write_scale(tmp_path, "short")
    flags = longform_flags(tmp_path)
    assert flags["m2_hybrid_retrieval"] is True
    assert flags["m3_canon_engine"] is True
    _write_scale(tmp_path, "medium")
    assert flag_enabled("m2_hybrid_retrieval", tmp_path) is True
    _write_scale(tmp_path, "epic")
    assert flag_enabled("m3_canon_engine", tmp_path) is True


def test_micro_keeps_memory_flags_off(tmp_path: Path):
    _write_scale(tmp_path, "micro")
    flags = longform_flags(tmp_path)
    assert flags["m2_hybrid_retrieval"] is False
    assert flags["m3_canon_engine"] is False


def test_yaml_override_wins_over_scale_default(tmp_path: Path):
    _write_scale(tmp_path, "medium")
    config = tmp_path / "config"
    config.mkdir()
    (config / "pipeline.yaml").write_text(
        "runtime:\n  longform_flags:\n    m2_hybrid_retrieval: false\n    m3_canon_engine: false\n",
        encoding="utf-8",
    )
    flags = longform_flags(tmp_path)
    assert flags["m2_hybrid_retrieval"] is False
    assert flags["m3_canon_engine"] is False
