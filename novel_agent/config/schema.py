"""Pydantic source of truth for pipeline configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONFIG_SCHEMA_VERSION = 2


class ExtensibleConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class RuntimeSettings(ExtensibleConfigModel):
    max_workers: int = Field(default=4, ge=1, le=8)
    retry_attempts: int = Field(default=1, ge=0, le=20)
    interactive: bool = False
    hook_fail_fast: bool = False
    hook_timeout_seconds: int = Field(default=30, ge=1, le=600)
    batch_fail_streak_max: int = Field(default=5, ge=1, le=100)


class ChapterSettings(ExtensibleConfigModel):
    default_target_chars: list[int] = Field(default_factory=lambda: [1200, 2200])
    default_scene_target_chars: list[int] = Field(default_factory=lambda: [400, 800])
    quality_mode: str = "report_only"

    @field_validator("default_target_chars", "default_scene_target_chars")
    @classmethod
    def validate_positive_range(cls, value: list[int]) -> list[int]:
        if len(value) != 2 or value[0] <= 0 or value[1] <= value[0]:
            raise ValueError("must contain two increasing positive integers")
        return value


class PipelineDocument(ExtensibleConfigModel):
    schema_version: Literal[2] = CONFIG_SCHEMA_VERSION
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    chapter: ChapterSettings = Field(default_factory=ChapterSettings)
    quality: dict[str, Any] = Field(default_factory=dict)
    llm: dict[str, Any] = Field(default_factory=lambda: {"provider": "static"})
    embedding: dict[str, Any] = Field(default_factory=lambda: {"provider": "stub"})


def pipeline_json_schema() -> dict[str, Any]:
    return PipelineDocument.model_json_schema()
