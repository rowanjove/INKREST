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

    compatible_spec = f"^{CORE_VERSION}"
    data = {
        'id': 'semver-test',
        'name': 'Semver Test',
        'plugin_type': 'web_extension',
        'entry': 'plugin:PLUGIN_CLASS',
        'version': '1.0.0',
        'engines': {'inkrest': compatible_spec},
    }
    normalized = validate_manifest(data, tmp_path)
    assert normalized['engines']['inkrest'] == compatible_spec
    assert normalized['min_core_version'] == compatible_spec

    major = int(CORE_VERSION.split('.')[0])
    incompat_spec = f"^{major + 1}.0.0"
    incompat = {
        'id': 'semver-future',
        'name': 'Future Plugin',
        'plugin_type': 'web_extension',
        'entry': 'plugin:PLUGIN_CLASS',
        'version': '1.0.0',
        'engines': {'inkrest': incompat_spec},
    }
    with pytest.raises(ManifestError) as exc_info:
        validate_manifest(incompat, tmp_path)
    assert incompat_spec in str(exc_info.value)
    assert CORE_VERSION in str(exc_info.value)
