import pytest
from pathlib import Path
from novel_agent.plugins.manifest import (
    parse_semver_range,
    is_core_version_compatible,
    validate_manifest,
    ManifestError,
    CORE_VERSION,
)



def test_parse_semver_range():
    assert parse_semver_range("^1.0.0") == ">=1.0.0, <2.0.0"
    assert parse_semver_range("^0.2.0") == ">=0.2.0, <0.3.0"
    assert parse_semver_range("^0.0.3") == "==0.0.3"
    assert parse_semver_range("~1.2.0") == ">=1.2.0, <1.3.0"
    assert parse_semver_range(">=1.0.0, <2.0.0") == ">=1.0.0, <2.0.0"
    assert parse_semver_range("1.0.0") == ">=1.0.0"
    assert parse_semver_range("*") == ">=0.0.0"


def test_is_core_version_compatible():
    assert is_core_version_compatible("^1.0.0", "1.0.0") is True
    assert is_core_version_compatible("^1.0.0", "1.5.2") is True
    assert is_core_version_compatible("^1.0.0", "2.0.0") is False
    assert is_core_version_compatible("^2.0.0", "1.0.0") is False
    assert is_core_version_compatible(">=1.0.0, <2.0.0", "1.2.0") is True
    assert is_core_version_compatible("~1.0.0", "1.0.5") is True
    assert is_core_version_compatible("~1.0.0", "1.1.0") is False


def test_validate_manifest_with_engines_inkrest(tmp_path: Path):
    (tmp_path / "plugin.py").write_text("class P: pass\nPLUGIN_CLASS = P\n", encoding="utf-8")

    data = {
        'id': 'semver-test',
        'name': 'Semver Test',
        'plugin_type': 'web_extension',
        'entry': 'plugin:PLUGIN_CLASS',
        'version': '1.0.0',
        'engines': {'inkrest': '^1.0.0'},
    }
    normalized = validate_manifest(data, tmp_path)
    assert normalized['engines']['inkrest'] == '^1.0.0'
    assert normalized['min_core_version'] == '^1.0.0'

    incompat = {
        'id': 'semver-future',
        'name': 'Future Plugin',
        'plugin_type': 'web_extension',
        'entry': 'plugin:PLUGIN_CLASS',
        'version': '1.0.0',
        'engines': {'inkrest': '^2.0.0'},
    }
    with pytest.raises(ManifestError) as exc_info:
        validate_manifest(incompat, tmp_path)
    assert "^2.0.0" in str(exc_info.value)
    assert "1.0.0" in str(exc_info.value)
