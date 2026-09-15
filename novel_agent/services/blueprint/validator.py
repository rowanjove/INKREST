from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from novel_agent.domain.blueprint.trope import TropeAtom


class ValidationIssue(BaseModel):
    level: str  # error | warning | suggestion
    code: str
    message: str
    affected_atoms: list[str] = Field(default_factory=list)
    suggestion: str = ""


class ValidationReport(BaseModel):
    is_valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    completeness_score: int = 100
    missing_elements: list[str] = Field(default_factory=list)


# Well-known narrative tension pairings that generate soft conflicts
KNOWN_TENSION_PAIRS: list[dict[str, Any]] = [
    {
        "pair": {"wudiliu", "shengcun"},
        "level": "warning",
        "code": "TENSION_OVERPOWERED_VS_SURVIVAL",
        "message": "「无敌流」与「绝境生存」组合存在叙事张力冲突：主角过于强大可能消解生存危机感。",
        "suggestion": "建议将威胁转移至身边的凡人队友、施加时效限制，或设定物理力量无法解决的规则困境。",
    },
    {
        "pair": {"xitong", "hard_scifi"},
        "level": "warning",
        "code": "TENSION_SYSTEM_VS_HARD_SCIFI",
        "message": "「系统流」与「硬科幻」在世界物理法则自洽性上容易产生撕裂感。",
        "suggestion": "建议为系统设定高等文明降维科技、量子纠缠观测器等自洽的硬核科学起源解释。",
    },
]


class BlueprintValidator:
    """Validates atoms and blueprints against dependency graphs and narrative rules."""

    def __init__(self, all_atoms: Optional[list[TropeAtom]] = None):
        self.atoms_map = {atom.id: atom for atom in (all_atoms or [])}

    def validate_atom_selection(self, selected_atom_ids: list[str]) -> ValidationReport:
        """Validates a set of selected trope atom IDs."""
        issues: list[ValidationIssue] = []
        selected_set = set(selected_atom_ids)

        # 1. Dependency checks (requires)
        for atom_id in selected_atom_ids:
            atom = self.atoms_map.get(atom_id)
            if not atom:
                continue
            for req in atom.requires:
                if req not in selected_set:
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            code="MISSING_REQUIREMENT",
                            message=f"「{atom.name}」通常需要搭配「{req}」以发挥最佳效果。",
                            affected_atoms=[atom_id, req],
                            suggestion=f"考虑在元件库中同时引入「{req}」。",
                        )
                    )

        # 2. Hard conflict checks (conflicts_with)
        for atom_id in selected_atom_ids:
            atom = self.atoms_map.get(atom_id)
            if not atom:
                continue
            for conf in atom.conflicts_with:
                if conf in selected_set:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            code="HARD_CONFLICT",
                            message=f"「{atom.name}」与已选项「{conf}」存在互斥冲突。",
                            affected_atoms=[atom_id, conf],
                            suggestion="建议二选一，或在故事设计中拆分为不同阶段展现。",
                        )
                    )

        # 3. Known narrative tension pairs
        for tension in KNOWN_TENSION_PAIRS:
            if tension["pair"].issubset(selected_set):
                issues.append(
                    ValidationIssue(
                        level=tension["level"],
                        code=tension["code"],
                        message=tension["message"],
                        affected_atoms=list(tension["pair"]),
                        suggestion=tension["suggestion"],
                    )
                )

        # 4. Completeness score
        missing = []
        has_channel = any(self.atoms_map.get(a) and self.atoms_map[a].type == "channel" for a in selected_atom_ids)
        has_genre = any(self.atoms_map.get(a) and self.atoms_map[a].type == "genre" for a in selected_atom_ids)
        has_mechanism = any(self.atoms_map.get(a) and self.atoms_map[a].type == "mechanism" for a in selected_atom_ids)
        has_cool_point = any(self.atoms_map.get(a) and self.atoms_map[a].type == "cool_point" for a in selected_atom_ids)

        if not has_channel:
            missing.append("频道/读者受众")
        if not has_genre:
            missing.append("主题材/世界外壳")
        if not has_mechanism:
            missing.append("核心推进机制/金手指")
        if not has_cool_point:
            missing.append("核心爽点/阅读快感")

        score = 100 - (len(missing) * 20) - (len([i for i in issues if i.level == "error"]) * 25)
        score = max(0, min(100, score))

        has_errors = any(i.level == "error" for i in issues)
        return ValidationReport(
            is_valid=not has_errors,
            issues=issues,
            completeness_score=score,
            missing_elements=missing,
        )
