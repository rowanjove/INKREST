"""Structured failure codes for API and background tasks."""

from novel_agent.errors.codes import (
    ERROR_HINTS,
    ErrorCode,
    classify_exception,
    failure_payload,
    http_error_detail,
)

__all__ = [
    "ErrorCode",
    "ERROR_HINTS",
    "classify_exception",
    "failure_payload",
    "http_error_detail",
]