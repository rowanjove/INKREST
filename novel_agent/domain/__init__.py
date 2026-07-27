"""Stable V2 domain contracts shared by persistence, HTTP, and desktop clients."""

from novel_agent.domain.project_snapshot import ProjectSnapshot
from novel_agent.domain.tasks import TaskRecord, TaskStatus, TaskType

__all__ = ["ProjectSnapshot", "TaskRecord", "TaskStatus", "TaskType"]
