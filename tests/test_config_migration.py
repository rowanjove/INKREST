from pathlib import Path

import pytest

from novel_agent.config.migration import apply_config_migration, inspect_config_migration


def test_legacy_config_is_inspected_without_mutation(tmp_path: Path):
    path = tmp_path / "pipeline.yaml"
    path.write_text("schema_version: 1\nmax_workers: 2\nllm:\n  provider: static\n", encoding="utf-8")
    plan = inspect_config_migration(path)
    assert plan.needs_migration is True
    assert path.read_text(encoding="utf-8").startswith("schema_version: 1")
    with pytest.raises(ValueError, match="explicit confirmation"):
        apply_config_migration(path, confirmation="")


def test_migration_backs_up_and_preserves_unknown_sections(tmp_path: Path):
    path = tmp_path / "pipeline.yaml"
    path.write_text("schema_version: 1\nmax_workers: 2\ncustom:\n  keep: true\n", encoding="utf-8")
    result = apply_config_migration(path, confirmation="MIGRATE pipeline.yaml")
    assert result["status"] == "migrated"
    assert Path(result["backup"]).is_file()
    text = path.read_text(encoding="utf-8")
    assert "schema_version: 2" in text
    assert "custom:" in text
    assert "max_workers: 2" in text
