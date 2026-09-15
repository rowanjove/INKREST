"""INKREST Layered Error IDs and User-Facing Presentation (Milestone B).

Formats internal and technical failures into customer-support friendly Error IDs
(e.g., INK-E-A21F7) with separated user guidance and technical diagnostics.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from novel_agent.errors.codes import ErrorCode, ERROR_HINTS, ERROR_ACTIONS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_error_id(category_code: str = "") -> str:
    """Generate a clean support-friendly error identifier like INK-E-A21F7."""
    token = secrets.token_hex(3).upper()[:5]
    return f"INK-E-{token}"


@dataclass
class UserFacingError:
    error_id: str
    error_code: ErrorCode
    title: str
    friendly_message: str
    user_action: str
    retryable: bool
    technical_details: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "code": self.error_code.value,
            "title": self.title,
            "message": self.friendly_message,
            "action": self.user_action,
            "retryable": self.retryable,
            "technical_details": self.technical_details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        code: ErrorCode = ErrorCode.UNKNOWN,
        title: str = "操作遇到问题",
    ) -> UserFacingError:
        error_id = generate_error_id()
        hint = ERROR_HINTS.get(code, "请稍后重试或查看技术详情。")
        action_meta = ERROR_ACTIONS.get(code, {"retryable": True, "user_action": "retry"})

        return cls(
            error_id=error_id,
            error_code=code,
            title=title,
            friendly_message=hint,
            user_action=action_meta.get("user_action", "retry"),
            retryable=action_meta.get("retryable", True),
            technical_details=f"{type(exc).__name__}: {str(exc)}",
        )
