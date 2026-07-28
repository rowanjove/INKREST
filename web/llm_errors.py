"""Helpers for turning model provider failures into actionable API errors."""

from __future__ import annotations

from fastapi import HTTPException


def model_provider_http_error(action: str, exc: Exception) -> HTTPException:
    message = str(exc)
    lowered = message.lower()
    if "401" in message or "authentication" in lowered or "api key" in lowered:
        detail = f"{action}失败：模型鉴权失败，请检查模型库里的 API Key、Base URL 和所选模型配置。{message}"
    elif "timeout" in lowered or "timed out" in lowered:
        detail = f"{action}失败：模型接口超时，请稍后重试或检查代理/模型服务状态。{message}"
    else:
        detail = f"{action}失败：模型接口返回异常。{message}"
    return HTTPException(502, detail)
