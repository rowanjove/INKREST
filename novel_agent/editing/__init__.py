"""Editing and Revision Control (Milestone E).

Provides:
- AI Diff Reviewer with chunk-by-chunk acceptance
- Command History with Undo / Redo
"""

from novel_agent.editing.diff_reviewer import (
    DiffReviewSession,
    DiffChunk,
    DiffChunkStatus,
    DiffChunkType,
)
from novel_agent.editing.command_history import (
    CommandHistory,
    BaseCommand,
    TextEditCommand,
    StateMutationCommand,
)

__all__ = [
    "DiffReviewSession",
    "DiffChunk",
    "DiffChunkStatus",
    "DiffChunkType",
    "CommandHistory",
    "BaseCommand",
    "TextEditCommand",
    "StateMutationCommand",
]
