"""Validated V2 configuration contracts and YAML persistence."""

from novel_agent.config.io import (
    ConfigEnvironmentError,
    ConfigValidationError,
    load_pipeline_document,
    redact_config_secrets,
    write_pipeline_document,
)
from novel_agent.config.schema import CONFIG_SCHEMA_VERSION, PipelineDocument

__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "ConfigEnvironmentError",
    "ConfigValidationError",
    "PipelineDocument",
    "load_pipeline_document",
    "redact_config_secrets",
    "write_pipeline_document",
]
