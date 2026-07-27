"""Machine-readable error codes and user-facing hints."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from novel_agent.exceptions import (
    FatalPipelineError,
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    RecoverablePipelineError,
    RetryExhaustedError,
    TaskAbortedError,
)


class ErrorCode(str, Enum):
    LLM_NOT_READY = "LLM_NOT_READY"
    ARC_QUEUE_STALE = "ARC_QUEUE_STALE"
    READINESS_BLOCKED = "READINESS_BLOCKED"
    CIRCUIT_PAUSED = "CIRCUIT_PAUSED"
    CHAPTER_ALREADY_RUNNING = "CHAPTER_ALREADY_RUNNING"
    NOVEL_BATCH_RUNNING = "NOVEL_BATCH_RUNNING"
    EXTERNAL_REVIEW_PENDING = "EXTERNAL_REVIEW_PENDING"
    LLM_AUTH = "LLM_AUTH"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RESPONSE = "LLM_RESPONSE"
    TASK_ABORTED = "TASK_ABORTED"
    RECOVERABLE_PIPELINE = "RECOVERABLE_PIPELINE"
    VALIDATION = "VALIDATION"
    UNKNOWN = "UNKNOWN"


ERROR_HINTS: Dict[ErrorCode, str] = {
    ErrorCode.LLM_NOT_READY: "请在「设置 → 模型路由」选择可用的日常模型（非 Static 占位）并填写 API Key。",
    ErrorCode.ARC_QUEUE_STALE: "卷队列与大纲不一致，请在工作台先点「同步卷队列」或重新 ensure-queue。",
    ErrorCode.READINESS_BLOCKED: "开书清单未就绪，请按监控/工作台提示补齐大纲、书名与核心资产。",
    ErrorCode.CIRCUIT_PAUSED: "全书因质量熔断已暂停，建议先改稿并重跑门禁，再在监控确认后续跑。",
    ErrorCode.CHAPTER_ALREADY_RUNNING: "该章节已有任务在跑，请等待完成或在运行监控中止后再试。",
    ErrorCode.NOVEL_BATCH_RUNNING: "全书批量任务已在运行，请等待结束后再启动新的续跑。",
    ErrorCode.EXTERNAL_REVIEW_PENDING: "有待外审章节未通过，请先在章节详情标记外审通过或关闭该门禁。",
    ErrorCode.LLM_AUTH: "模型 API 认证失败，请检查 Key 是否有效、是否过期。",
    ErrorCode.LLM_RATE_LIMIT: "模型 API 触发限流，请稍后重试或切换备用模型。",
    ErrorCode.LLM_TIMEOUT: "模型请求超时，可重试单章或降低并发。",
    ErrorCode.LLM_RESPONSE: "模型返回格式异常，可重跑审校或单章。",
    ErrorCode.TASK_ABORTED: "任务已被用户中止。",
    ErrorCode.RECOVERABLE_PIPELINE: "本章可重试：查看运行日志后补跑单章或只重跑门禁。",
    ErrorCode.VALIDATION: "请求参数或项目状态无效，请按提示修正后重试。",
    ErrorCode.UNKNOWN: "发生未分类错误，请查看 logs/novel_agent.log 或运行监控日志。",
}

ERROR_ACTIONS: Dict[ErrorCode, Dict[str, Any]] = {
    ErrorCode.LLM_NOT_READY: {"retryable": False, "user_action": "configure_model"},
    ErrorCode.ARC_QUEUE_STALE: {"retryable": False, "user_action": "sync_arc_queue"},
    ErrorCode.READINESS_BLOCKED: {"retryable": False, "user_action": "complete_readiness"},
    ErrorCode.CIRCUIT_PAUSED: {"retryable": False, "user_action": "repair_and_rerun_gate"},
    ErrorCode.CHAPTER_ALREADY_RUNNING: {"retryable": False, "user_action": "wait_or_abort_existing_task"},
    ErrorCode.NOVEL_BATCH_RUNNING: {"retryable": False, "user_action": "wait_for_batch"},
    ErrorCode.EXTERNAL_REVIEW_PENDING: {"retryable": False, "user_action": "complete_external_review"},
    ErrorCode.LLM_AUTH: {"retryable": False, "user_action": "fix_model_auth"},
    ErrorCode.LLM_RATE_LIMIT: {"retryable": True, "user_action": "retry_later_or_switch_model"},
    ErrorCode.LLM_TIMEOUT: {"retryable": True, "user_action": "retry_or_reduce_concurrency"},
    ErrorCode.LLM_RESPONSE: {"retryable": True, "user_action": "rerun_step"},
    ErrorCode.TASK_ABORTED: {"retryable": False, "user_action": "restart_task_if_needed"},
    ErrorCode.RECOVERABLE_PIPELINE: {"retryable": True, "user_action": "resume_or_rerun_chapter"},
    ErrorCode.VALIDATION: {"retryable": False, "user_action": "fix_request"},
    ErrorCode.UNKNOWN: {"retryable": False, "user_action": "inspect_logs"},
}


def _code_from_message(message: str) -> Optional[ErrorCode]:
    text = (message or "").lower()
    if "novel batch already running" in text or "全书批量" in message:
        return ErrorCode.NOVEL_BATCH_RUNNING
    if "already running" in text or "已在运行" in message:
        return ErrorCode.CHAPTER_ALREADY_RUNNING
    if "arc_queue_stale" in text or "卷队列" in message and "同步" in message:
        return ErrorCode.ARC_QUEUE_STALE
    if "static" in text or "日常模型" in message:
        return ErrorCode.LLM_NOT_READY
    if "circuit" in text or "熔断" in message:
        return ErrorCode.CIRCUIT_PAUSED
    if "外审" in message or "external" in text:
        return ErrorCode.EXTERNAL_REVIEW_PENDING
    if "readiness" in text or "开书" in message or "pending" in text:
        return ErrorCode.READINESS_BLOCKED
    return None


def classify_exception(exc: BaseException) -> Tuple[ErrorCode, str]:
    if isinstance(exc, FatalPipelineError):
        guessed = _code_from_message(str(exc))
        code = guessed or ErrorCode.LLM_NOT_READY
        return code, ERROR_HINTS.get(code, str(exc))
    if isinstance(exc, LLMAuthError):
        return ErrorCode.LLM_AUTH, ERROR_HINTS[ErrorCode.LLM_AUTH]
    if isinstance(exc, LLMRateLimitError):
        return ErrorCode.LLM_RATE_LIMIT, ERROR_HINTS[ErrorCode.LLM_RATE_LIMIT]
    if isinstance(exc, LLMTimeoutError):
        return ErrorCode.LLM_TIMEOUT, ERROR_HINTS[ErrorCode.LLM_TIMEOUT]
    if isinstance(exc, (LLMResponseError, RetryExhaustedError)):
        return ErrorCode.LLM_RESPONSE, ERROR_HINTS[ErrorCode.LLM_RESPONSE]
    if isinstance(exc, TaskAbortedError):
        return ErrorCode.TASK_ABORTED, ERROR_HINTS[ErrorCode.TASK_ABORTED]
    if isinstance(exc, RecoverablePipelineError):
        return ErrorCode.RECOVERABLE_PIPELINE, ERROR_HINTS[ErrorCode.RECOVERABLE_PIPELINE]
    if isinstance(exc, ValueError):
        guessed = _code_from_message(str(exc))
        if guessed:
            return guessed, ERROR_HINTS.get(guessed, str(exc))
        return ErrorCode.VALIDATION, str(exc) or ERROR_HINTS[ErrorCode.VALIDATION]
    guessed = _code_from_message(str(exc))
    if guessed:
        return guessed, ERROR_HINTS.get(guessed, str(exc))
    return ErrorCode.UNKNOWN, str(exc) or ERROR_HINTS[ErrorCode.UNKNOWN]


def failure_payload(
    exc: BaseException,
    *,
    resumable_from: Optional[str] = None,
) -> Dict[str, Any]:
    code, hint = classify_exception(exc)
    payload: Dict[str, Any] = {
        "failure_kind": code.value,
        "failure_hint": hint,
        "code": code.value,
        "message": str(exc).strip() or hint,
        **ERROR_ACTIONS.get(code, ERROR_ACTIONS[ErrorCode.UNKNOWN]),
    }
    if resumable_from:
        payload["resumable_from"] = resumable_from
    return payload


def http_error_detail(
    code: ErrorCode,
    message: Optional[str] = None,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "code": code.value,
        "detail": message or ERROR_HINTS.get(code, code.value),
        "hint": ERROR_HINTS.get(code, ""),
        **ERROR_ACTIONS.get(code, ERROR_ACTIONS[ErrorCode.UNKNOWN]),
    }
    if extra:
        body.update(extra)
    return body
