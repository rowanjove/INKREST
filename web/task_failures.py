"""Map task exceptions to structured failure metadata."""

from __future__ import annotations

from typing import Any, Dict, Optional

from novel_agent.errors import classify_exception, failure_payload


def task_failure_result(
    exc: BaseException,
    *,
    resumable_from: Optional[str] = None,
) -> Dict[str, Any]:
    return failure_payload(exc, resumable_from=resumable_from)


def task_failure_error_string(exc: BaseException) -> str:
    code, hint = classify_exception(exc)
    msg = str(exc).strip()
    if msg and msg != hint:
        return f"[{code.value}] {msg}"
    return f"[{code.value}] {hint}"