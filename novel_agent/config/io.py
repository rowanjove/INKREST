"""Validated YAML loading, environment resolution, redaction, and atomic writes."""

from __future__ import annotations

import copy
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from novel_agent.config.schema import CONFIG_SCHEMA_VERSION, PipelineDocument


_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")
_SECRET_KEYS = frozenset(
    {"api_key", "api_token", "access_token", "secret", "password"}
)
SECRET_MASK = "********"


class ConfigValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]):
        self.errors = errors
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', ())) or 'document'}: "
            f"{error.get('msg', 'invalid value')}"
            for error in errors
        )
        super().__init__(details or "Invalid pipeline configuration")


class ConfigEnvironmentError(ConfigValidationError):
    pass


def _safe_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(error.get("loc") or []),
            "msg": str(error.get("msg") or "invalid value"),
            "type": str(error.get("type") or "validation_error"),
        }
        for error in exc.errors()
    ]


def _resolve_environment(value: Any) -> Any:
    if isinstance(value, str):
        missing = [
            name for name in _ENV_VAR_RE.findall(value) if os.environ.get(name) is None
        ]
        if missing:
            raise ConfigEnvironmentError(
                [
                    {
                        "loc": ["environment", name],
                        "msg": f"Environment variable {name} is not set",
                        "type": "missing_environment_variable",
                    }
                    for name in missing
                ]
            )
        return _ENV_VAR_RE.sub(lambda match: os.environ[match.group(1)], value)
    if isinstance(value, dict):
        return {key: _resolve_environment(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_environment(item) for item in value]
    return value


def resolve_environment_values(value: Any) -> Any:
    """Resolve ${NAME} placeholders or raise when a required variable is absent."""

    return _resolve_environment(value)


def validate_pipeline_document(data: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(data)
    normalized.setdefault("schema_version", CONFIG_SCHEMA_VERSION)
    try:
        document = PipelineDocument.model_validate(normalized)
    except ValidationError as exc:
        raise ConfigValidationError(_safe_validation_errors(exc)) from exc
    result = document.model_dump(mode="python", exclude_unset=True)
    result["schema_version"] = CONFIG_SCHEMA_VERSION
    return result


def load_pipeline_document(
    path: Path,
    *,
    resolve_environment: bool = True,
) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return {}
    try:
        loaded = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            [
                {
                    "loc": [],
                    "msg": "Invalid YAML syntax",
                    "type": "yaml_syntax",
                }
            ]
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise ConfigValidationError(
            [{"loc": [], "msg": "Configuration file could not be read", "type": "io_error"}]
        ) from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError(
            [
                {
                    "loc": [],
                    "msg": "Pipeline configuration root must be an object",
                    "type": "object_type",
                }
            ]
        )
    if resolve_environment:
        loaded = _resolve_environment(loaded)
    return validate_pipeline_document(loaded)


def write_pipeline_document(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    target = Path(path)
    validated = validate_pipeline_document(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            yaml.safe_dump(
                validated,
                stream,
                allow_unicode=True,
                sort_keys=False,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return validated


def redact_config_secrets(data: dict[str, Any]) -> dict[str, Any]:
    def redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: SECRET_MASK if key.lower() in _SECRET_KEYS and item else redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    return redact(copy.deepcopy(data))
