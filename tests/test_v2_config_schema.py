from __future__ import annotations

import os

import pytest
import yaml

from novel_agent.config.io import (
    ConfigEnvironmentError,
    ConfigValidationError,
    load_pipeline_document,
    redact_config_secrets,
    write_pipeline_document,
)
from novel_agent.config.schema import (
    CONFIG_SCHEMA_VERSION,
    PipelineDocument,
    pipeline_json_schema,
)
from novel_agent.pipeline import PipelineConfig, load_pipeline_settings


def test_default_pipeline_document_uses_v2_schema():
    document = PipelineDocument()

    assert document.schema_version == CONFIG_SCHEMA_VERSION == 2
    assert document.runtime.max_workers == 4
    assert document.chapter.default_target_chars == [1200, 2200]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("runtime: [broken", "YAML"),
        ("- not\n- an\n- object\n", "object"),
        ("runtime:\n  max_workers: 0\n", "max_workers"),
        ("chapter:\n  default_target_chars: [2200, 1200]\n", "default_target_chars"),
    ],
)
def test_invalid_documents_raise_structured_errors(tmp_path, content, expected):
    path = tmp_path / "pipeline.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigValidationError) as raised:
        load_pipeline_document(path)

    assert expected.lower() in str(raised.value).lower()
    assert raised.value.errors


def test_missing_environment_variable_is_not_replaced_with_empty_text(tmp_path, monkeypatch):
    monkeypatch.delenv("V2_MISSING_API_KEY", raising=False)
    path = tmp_path / "pipeline.yaml"
    path.write_text(
        "llm:\n  default:\n    api_key: ${V2_MISSING_API_KEY}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigEnvironmentError, match="V2_MISSING_API_KEY"):
        load_pipeline_document(path)


def test_generic_settings_preserve_placeholder_but_runtime_resolution_fails(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("V2_RUNTIME_API_KEY", raising=False)
    config = tmp_path / "config"
    config.mkdir()
    (config / "pipeline.yaml").write_text(
        "llm:\n"
        "  provider: openai\n"
        "  api_key: ${V2_RUNTIME_API_KEY}\n"
        "embedding:\n  provider: stub\n",
        encoding="utf-8",
    )

    settings = load_pipeline_settings(tmp_path)

    assert settings["llm"]["api_key"] == "${V2_RUNTIME_API_KEY}"
    with pytest.raises(ConfigEnvironmentError, match="V2_RUNTIME_API_KEY"):
        PipelineConfig.from_config(tmp_path)


def test_atomic_write_adds_schema_version_and_preserves_original_on_replace_failure(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "pipeline.yaml"
    path.write_text("runtime:\n  max_workers: 2\n", encoding="utf-8")
    original = path.read_text(encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        write_pipeline_document(path, {"runtime": {"max_workers": 3}})

    assert path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob(".pipeline.yaml.*.tmp"))


def test_atomic_write_round_trips_and_has_no_temp_file(tmp_path):
    path = tmp_path / "pipeline.yaml"

    saved = write_pipeline_document(
        path,
        {
            "runtime": {"max_workers": 3},
            "chapter": {"default_target_chars": [1000, 1800]},
            "plugin_extension": {"enabled": True},
        },
    )

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2
    assert raw["plugin_extension"] == {"enabled": True}
    assert saved == load_pipeline_document(path)
    assert not list(tmp_path.glob(".pipeline.yaml.*.tmp"))


def test_secret_redaction_is_recursive_without_masking_token_limits():
    redacted = redact_config_secrets(
        {
            "llm": {
                "api_key": "sk-secret",
                "access_token": "token-secret",
                "max_tokens": 8192,
            },
            "password": "secret",
        }
    )

    assert redacted["llm"]["api_key"] == "********"
    assert redacted["llm"]["access_token"] == "********"
    assert redacted["llm"]["max_tokens"] == 8192
    assert redacted["password"] == "********"


def test_json_schema_exposes_form_sections_and_version():
    schema = pipeline_json_schema()

    assert schema["properties"]["schema_version"]["const"] == 2
    assert {"runtime", "chapter", "quality", "llm", "embedding"} <= set(
        schema["properties"]
    )
