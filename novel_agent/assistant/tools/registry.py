"""Tool Registry and Permission System for ShanShan Assistant.

Enforces Permission Levels (0 to 5):
Level 0: Read Only (Auto-allowed)
Level 1: Search & Analysis (Auto-allowed)
Level 2: Model Generation (User action allowed)
Level 3: Patch Proposal (Allowed to propose, user confirms write)
Level 4: Project Structure Mutation (Explicit confirm required)
Level 5: Delete / Danger / Full-book (Strong confirm required)
"""

from __future__ import annotations

from enum import IntEnum
import inspect
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionLevel(IntEnum):
    LEVEL_0_READ = 0
    LEVEL_1_SEARCH = 1
    LEVEL_2_GENERATE = 2
    LEVEL_3_PROPOSAL = 3
    LEVEL_4_MUTATION = 4
    LEVEL_5_DANGER = 5


class ToolDefinition(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False


class RegisteredTool:
    def __init__(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Any],
    ):
        self.definition = definition
        self.handler = handler

    async def execute(self, **kwargs) -> Any:
        if inspect.iscoroutinefunction(self.handler):
            return await self.handler(**kwargs)
        return self.handler(**kwargs)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        permission_level: PermissionLevel,
        handler: Callable[..., Any],
        parameters_schema: Optional[Dict[str, Any]] = None,
        requires_confirmation: Optional[bool] = None,
    ) -> None:
        if requires_confirmation is None:
            requires_confirmation = permission_level >= PermissionLevel.LEVEL_3_PROPOSAL

        definition = ToolDefinition(
            name=name,
            description=description,
            permission_level=permission_level,
            parameters_schema=parameters_schema or {},
            requires_confirmation=requires_confirmation,
        )
        self._tools[name] = RegisteredTool(definition, handler)

    def get(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    def list_definitions(self) -> List[ToolDefinition]:
        return [t.definition for t in self._tools.values()]

    def can_auto_execute(self, tool_name: str) -> bool:
        tool = self.get(tool_name)
        if not tool:
            return False
        # Level 0 and 1 are safe to auto-execute during agent reasoning loop
        return tool.definition.permission_level <= PermissionLevel.LEVEL_1_SEARCH


_global_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _global_tool_registry
    if _global_tool_registry is None:
        _global_tool_registry = ToolRegistry()
    return _global_tool_registry
