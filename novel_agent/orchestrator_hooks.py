"""Pipeline plugin hook dispatch with timeout and fail-fast policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from novel_agent.logging_config import get_logger
from novel_agent.plugins.hook_runner import call_hook_with_timeout, resolve_hook_timeout_seconds
from novel_agent.progress import emit_hook_warning

logger = get_logger("orchestrator.hooks")

T = TypeVar("T")


class HookDispatcher:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def fail_fast(self) -> bool:
        from novel_agent.pipeline import load_pipeline_settings

        return bool(
            load_pipeline_settings(self.root_dir).get("runtime", {}).get("hook_fail_fast", False)
        )

    def timeout_seconds(self) -> float:
        return resolve_hook_timeout_seconds(self.root_dir)

    def call(
        self,
        hook_name: str,
        chapter_id: str,
        fn: Callable[[], T],
        default: Optional[T] = None,
    ) -> T:
        try:
            return call_hook_with_timeout(
                fn,
                timeout_seconds=self.timeout_seconds(),
                default=default,
            )
        except TimeoutError as exc:
            self._on_error(hook_name, exc, chapter_id)
            return default  # type: ignore[return-value]
        except Exception as exc:
            self._on_error(hook_name, exc, chapter_id)
            return default  # type: ignore[return-value]

    def _on_error(self, hook_name: str, exc: Exception, chapter_id: str = "") -> None:
        logger.error("Error in hook %s: %s", hook_name, exc)
        emit_hook_warning(hook_name, str(exc), chapter_id)
        if self.fail_fast():
            raise exc