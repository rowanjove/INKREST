"""SkillRegistry - Loads, manages, and matches AI editorial skills for ShanShan."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml


class SkillDefinition(BaseModel):
    id: str
    name: str
    command: str
    description: str = ""
    produces_patch: bool = False
    system_instruction: str = ""


class SkillRegistry:
    _instance: Optional[SkillRegistry] = None

    def __init__(self, definitions_dir: Optional[Path] = None):
        if not definitions_dir:
            definitions_dir = Path(__file__).parent / "definitions"
        self.definitions_dir = definitions_dir
        self._skills: Dict[str, SkillDefinition] = {}
        self.load_definitions()

    def load_definitions(self) -> None:
        self._skills.clear()
        if not self.definitions_dir.is_dir():
            return
        for file in self.definitions_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data and "name" in data:
                    skill = SkillDefinition(**data)
                    self._skills[skill.id] = skill
            except Exception:
                continue

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        return self._skills.get(skill_id)

    def find_by_command(self, text: str) -> Optional[SkillDefinition]:
        """Detect if message starts with a slash command, e.g. '/润色 这段文笔不行'."""
        first_token = text.strip().split()[0] if text.strip() else ""
        for skill in self._skills.values():
            if first_token == skill.command:
                return skill
        return None

    def list_skills(self) -> List[SkillDefinition]:
        return list(self._skills.values())


_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
