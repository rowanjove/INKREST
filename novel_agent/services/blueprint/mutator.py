"""Story Mutator for diversifying tropes across conservative, moderate, and radical branches."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MutationVariant(BaseModel):
    mutation_level: str  # conservative | moderate | radical
    level_label: str
    headline: str
    description: str
    suggested_atoms: list[str] = Field(default_factory=list)
    novelty_twist: str


class MutationResult(BaseModel):
    original_atoms: list[str]
    locked_dimensions: list[str] = Field(default_factory=list)
    variants: list[MutationVariant] = Field(default_factory=list)


class StoryMutator:
    """Mutates an existing trope combination into differentiated creative branches."""

    @staticmethod
    def mutate(
        current_atom_ids: list[str],
        locked_dimensions: list[str] | None = None,
    ) -> MutationResult:
        locked = set(locked_dimensions or [])
        current_set = set(current_atom_ids)

        # 1. Conservative Mutation: Retain foundation, substitute mechanism or twist cool point
        cons_atoms = list(current_atom_ids)
        twist_cons = "保留主基调与世界结构，将常规金手指升级为具备成长代价的模拟器/因果置换。"
        if "xitong" in cons_atoms and "mechanisms" not in locked:
            cons_atoms.remove("xitong")
            cons_atoms.append("chongsheng")
            twist_cons = "将系统流微调为重生先知流，降低机械降神感，强化主角自身智斗与信息差优势。"

        conservative = MutationVariant(
            mutation_level="conservative",
            level_label="保守变异（稳健调优）",
            headline="机制去模板化 · 强化个人博弈",
            description="在符合主流网文期待的前提下，替换套路中最易疲劳的环节，强化主角能动性。",
            suggested_atoms=cons_atoms,
            novelty_twist=twist_cons,
        )

        # 2. Moderate Mutation: Role reversal or narrative structure flip
        mod_atoms = [a for a in current_atom_ids if a != "dalian"]
        if "cool_points" not in locked:
            mod_atoms.append("fuchou")
            mod_atoms.append("jiushu")

        moderate = MutationVariant(
            mutation_level="moderate",
            level_label="中等变异（角色与叙事反转）",
            headline="身份错位 · 从逆袭打脸到幕后经营",
            description="主角不再是常规的单纯草根升级者，而是自带隐秘身份或背负拯救宿命的破局者。",
            suggested_atoms=mod_atoms,
            novelty_twist="主角从被动应战转变为主动设局，利用世界规则反向收割敌人，将单体战斗升级为群体博弈。",
        )

        # 3. Radical Mutation: Deconstruct tropes, cross-genre collision
        rad_atoms = ["kehuan", "wuxianliu", "shengcun"] if "genre" not in locked else current_atom_ids[:2] + ["shengcun"]
        radical = MutationVariant(
            mutation_level="radical",
            level_label="激进变异（破局重构）",
            headline="题材碰撞与规则解构 · 打造极高辨识度",
            description="引入高维度对抗与不可名状规则约束，将常规爽点升华为文明层面的突破。",
            suggested_atoms=rad_atoms,
            novelty_twist="金手指并非纯粹福利，而是高维文明留下的观测仪器；主角每一次升级都在触碰世界终极真相的残酷边界。",
        )

        return MutationResult(
            original_atoms=current_atom_ids,
            locked_dimensions=list(locked),
            variants=[conservative, moderate, radical],
        )
