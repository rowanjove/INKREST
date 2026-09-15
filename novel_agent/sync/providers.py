"""Sync Provider abstractions and local fallbacks (Milestone F).

Enables future cloud sync integration without rewriting data layer.
"""

from __future__ import annotations

import abc
from typing import List, Tuple
from novel_agent.sync.journal import JournalEntry


class BaseSyncProvider(abc.ABC):
    """Abstract interface for multi-device sync backends."""

    @abc.abstractmethod
    def push_deltas(self, entries: List[JournalEntry]) -> Tuple[bool, str]:
        """Push local deltas to cloud."""
        pass

    @abc.abstractmethod
    def pull_deltas(self, since_seq: int) -> Tuple[List[JournalEntry], int]:
        """Pull remote deltas from cloud."""
        pass


class NoopSyncProvider(BaseSyncProvider):
    """Local-only provider (no-op)."""

    def push_deltas(self, entries: List[JournalEntry]) -> Tuple[bool, str]:
        return True, "本地运行模式：未配置云端同步"

    def pull_deltas(self, since_seq: int) -> Tuple[List[JournalEntry], int]:
        return [], since_seq
