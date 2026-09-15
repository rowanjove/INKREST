"""Command History and Transactional Undo/Redo Engine (Milestone E).

Provides immediate workflow undo/redo for AI rewrites, batch polishing,
character editing, and outline restructuring, complementing long-term Revisions.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseCommand(abc.ABC):
    """Abstract reversible command."""

    def __init__(self, description: str) -> None:
        self.command_id = f"cmd_{uuid.uuid4().hex[:8]}"
        self.description = description
        self.executed_at = now_iso()

    @abc.abstractmethod
    def execute(self) -> Any:
        """Apply the forward mutation."""
        pass

    @abc.abstractmethod
    def undo(self) -> Any:
        """Revert the mutation."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "description": self.description,
            "executed_at": self.executed_at,
            "type": self.__class__.__name__,
        }


class TextEditCommand(BaseCommand):
    """Reversible command for chapter or document text edits."""

    def __init__(
        self,
        description: str,
        setter_func: Callable[[str], None],
        old_text: str,
        new_text: str,
    ) -> None:
        super().__init__(description)
        self.setter_func = setter_func
        self.old_text = old_text
        self.new_text = new_text

    def execute(self) -> str:
        self.setter_func(self.new_text)
        return self.new_text

    def undo(self) -> str:
        self.setter_func(self.old_text)
        return self.old_text


class StateMutationCommand(BaseCommand):
    """Reversible command for generic state or setting dictionaries."""

    def __init__(
        self,
        description: str,
        setter_func: Callable[[Dict[str, Any]], None],
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
    ) -> None:
        super().__init__(description)
        self.setter_func = setter_func
        self.old_state = dict(old_state)
        self.new_state = dict(new_state)

    def execute(self) -> Dict[str, Any]:
        self.setter_func(self.new_state)
        return self.new_state

    def undo(self) -> Dict[str, Any]:
        self.setter_func(self.old_state)
        return self.old_state


class CommandHistory:
    """Manages undo/redo stacks for active editing sessions."""

    def __init__(self, max_depth: int = 100) -> None:
        self.max_depth = max_depth
        self._undo_stack: List[BaseCommand] = []
        self._redo_stack: List[BaseCommand] = []

    def execute(self, command: BaseCommand) -> Any:
        """Execute a command and push to undo stack, clearing redo stack."""
        result = command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        return result

    def undo(self) -> Optional[BaseCommand]:
        """Undo the most recent command."""
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return command

    def redo(self) -> Optional[BaseCommand]:
        """Redo the most recently undone command."""
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        return command

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def list_undo_history(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in reversed(self._undo_stack)]

    def list_redo_history(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in reversed(self._redo_stack)]

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
