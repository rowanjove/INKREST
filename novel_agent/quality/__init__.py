"""Quality gates for generated chapters."""

from .hooks import extract_tail_hooks, check_head_continuity

__all__ = ["extract_tail_hooks", "check_head_continuity"]

