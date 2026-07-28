"""Custom exceptions for the novel agent system."""


class AgentError(Exception):
    """Base exception for all agent errors."""


class LLMResponseError(AgentError):
    """LLM returned malformed or unparseable output."""


class RetryExhaustedError(AgentError):
    """All retry attempts have been exhausted."""


class LLMTimeoutError(AgentError):
    """LLM API call timed out."""


class LLMAuthError(AgentError):
    """LLM API authentication failed (non-retryable)."""


class LLMRateLimitError(AgentError):
    """LLM API rate limit hit (retryable after backoff)."""


class StateError(AgentError):
    """Novel state corruption or validation error."""


class ValidationError(AgentError):
    """Input validation failed."""


class PipelineError(AgentError):
    """Pipeline execution error."""


class RecoverablePipelineError(PipelineError):
    """Non-fatal pipeline failure; caller may retry or skip."""

    def __init__(self, message: str, *, chapter_id: str = ""):
        super().__init__(message)
        self.chapter_id = chapter_id


class FatalPipelineError(PipelineError):
    """Unrecoverable pipeline failure; stop the current chapter or batch."""


class TaskAbortedError(AgentError):
    """Task aborted by user."""

