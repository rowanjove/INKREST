from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from novel_agent.domain.blueprint.blueprint import (
    ChannelSpec,
    CharacterArc,
    EmotionSpec,
    GenreSpec,
    MechanismSpec,
    NarrativeSpec,
    PacingPlan,
    PacingVolume,
    ProtagonistSpec,
    ReaderPromise,
    StoryBlueprint,
    StoryDNA,
    USP,
    WorldConstraintRule,
    WorldSpec,
)
from novel_agent.domain.blueprint.recipe import TropeRecipe
from novel_agent.domain.blueprint.trope import TropeAtom


class BlueprintCompiler:
    """Compiles Trope atoms, recipes, and user overrides into a unified StoryBlueprint."""

    def __init__(
        self,
        all_atoms: Optional[list[TropeAtom]] = None,
        all_recipes: Optional[list[TropeRecipe]] = None,
    ):
        self.atoms_map = {a.id: a for a in (all_atoms or [])}
        self.recipes_map = {r.id: r for r in (all_recipes or [])}

    def compile(
        self,
        selected_atom_ids: list[str],
        recipe_id: Optional[str] = None,
        user_inputs: Optional[dict[str, Any]] = None,
        project_id: str = "",
    ) -> StoryBlueprint:
        inputs = user_inputs or {}
        recipe = self.recipes_map.get(recipe_id) if recipe_id else None

        # If a recipe is selected, merge its atoms into selection
        combined_atom_ids = list(selected_atom_ids)
        if recipe:
            for aid in recipe.atoms:
                if aid not in combined_atom_ids:
                    combined_atom_ids.append(aid)

        # 1. Resolve atoms by dimension
        channels: list[TropeAtom] = []
        genres: list[TropeAtom] = []
        mechanisms: list[TropeAtom] = []
        cool_points: list[TropeAtom] = []

        for aid in combined_atom_ids:
            atom = self.atoms_map.get(aid)
            if not atom:
                continue
            if atom.type == "channel":
                channels.append(atom)
            elif atom.type == "genre":
                genres.append(atom)
            elif atom.type == "mechanism":
                mechanisms.append(atom)
            elif atom.type == "cool_point":
                cool_points.append(atom)

        # 2. Build Story DNA
        primary_channel = channels[0] if channels else None
        channel_spec = ChannelSpec(
            id=primary_channel.id if primary_channel else "general",
            label=primary_channel.name if primary_channel else "通用",
        )

        primary_genre = genres[0] if genres else None
        secondary_genres = [g.name for g in genres[1:]]
        genre_spec = GenreSpec(
            primary=primary_genre.name if primary_genre else "通用",
            secondary=secondary_genres,
        )

        protagonist_name = inputs.get("protagonist_name", "主角")
        protagonist_archetype = inputs.get("protagonist_archetype", "坚毅果敢的小人物")
        protagonist_spec = ProtagonistSpec(
            name=protagonist_name,
            archetype=protagonist_archetype,
            identity=inputs.get("protagonist_identity", "普通开局"),
            core_desire=inputs.get("core_desire", "在这个世界立足并逐步掌控自身命运"),
            flaw=inputs.get("protagonist_flaw", "行事偶有偏执或谨慎过甚"),
        )

        world_spec = WorldSpec(
            structure=inputs.get("world_structure", "阶层固化的庞大世界体系"),
            scarcity=inputs.get("world_scarcity", "稀缺上升通道与核心修行/生存资源"),
            power_system=inputs.get("power_system", "层层递进的等级考核/境界体系"),
            core_conflict=inputs.get("core_conflict", "底层草根突破既定命运与垄断利益集团之间的冲突"),
        )

        mechanism_specs = [
            MechanismSpec(
                id=m.id,
                name=m.name,
                category="gold_finger",
                parameters=inputs.get("mechanism_params", {}).get(m.id, {}),
            )
            for m in mechanisms
        ]

        emotion_specs = [
            EmotionSpec(
                id=cp.id,
                name=cp.name,
                frequency="medium",
            )
            for cp in cool_points
        ]

        narrative_spec = NarrativeSpec(
            structure=inputs.get("narrative_structure", "linear_progression"),
            viewpoint="third_person_limited",
            pacing="fast",
            style_tone=inputs.get("style_tone", "节奏紧凑、期待明确"),
        )

        dna = StoryDNA(
            channel=channel_spec,
            genres=genre_spec,
            protagonist=protagonist_spec,
            world=world_spec,
            mechanisms=mechanism_specs,
            core_conflict=world_spec.core_conflict,
            emotional_engines=emotion_specs,
            narrative=narrative_spec,
        )

        # 3. Formulate USP
        one_sentence_hook = inputs.get(
            "one_sentence_hook",
            f"一个身处{world_spec.structure}的{protagonist_archetype}，依靠{', '.join([m.name for m in mechanisms]) or '独门机变'}实现逆势崛起的故事。",
        )
        usp = USP(
            one_sentence_hook=one_sentence_hook,
            core_fantasy=[cp.name for cp in cool_points] or ["成长", "掌控命运"],
            novelty_points=[m.name for m in mechanisms] or ["新颖机制对抗"],
            reader_promise_summary="每 3-5 章提供明确的阶段回报与实力/认知进阶，长线悬念在卷末集中爆发。",
        )

        # 4. Synthesize Reader Promises
        reader_promises = [
            ReaderPromise(
                id="progression_payoff",
                promise_type="progression",
                description="主角实力、地位或信息差在关键剧情节点产生显著质变",
                expected_interval="5-10",
                payoff_stage="every_volume_mid_and_end",
            ),
            ReaderPromise(
                id="conflict_resolution",
                promise_type="emotional_payoff",
                description="前置铺垫的敌对压制必须在对应小高潮完成彻底反转与打脸",
                expected_interval="3-6",
                payoff_stage="volume_subclimaxes",
            ),
        ]

        # 5. Build Pacing Plan
        pacing = PacingPlan(
            target_chapters=int(inputs.get("target_chapters", 100)),
            rhythm_pattern="web_novel_three_act_serial",
            volumes=[
                PacingVolume(
                    volume_index=1,
                    title="第一卷：破局立足",
                    opening_hook=9,
                    climax_target=9,
                    cool_points=[cp.name for cp in cool_points[:2]] if cool_points else ["初次爆发"],
                ),
                PacingVolume(
                    volume_index=2,
                    title="第二卷：锋芒毕露",
                    opening_hook=7,
                    climax_target=10,
                    cool_points=[cp.name for cp in cool_points[2:4]] if len(cool_points) > 2 else ["名扬四方"],
                ),
            ],
        )

        # 6. Character Arc
        character_arcs = [
            CharacterArc(
                character_name=protagonist_name,
                start_belief="只求在乱局中苟全性命",
                want="安全与稳定",
                need="承担责任，建立自己的规则与秩序",
                midpoint_crisis="被逼入死角，单纯妥协退让不再有效",
                end_belief="命运只能由自己亲手书写",
            )
        ]

        # 7. World Constraints
        world_constraints = [
            WorldConstraintRule(
                name="力量守恒与金手指限制",
                rule_type="power_law",
                condition=[f"使用机制「{m.name}」时" for m in mechanisms] or ["突破极限时"],
                forbidden=["无消耗无限瞬杀", "直接推翻既定世界底层因果律"],
                consequences=["精神反噬或机能冷却惩罚", "引来高位势力的注意与警觉"],
            )
        ]

        # 8. Render Writing Guide Markdown
        writing_guide_md = self._render_writing_guide(
            title=inputs.get("title", "未命名故事"),
            dna=dna,
            usp=usp,
            recipe=recipe,
            reader_promises=reader_promises,
            pacing=pacing,
        )

        # 9. Outline Contract JSON
        outline_contract = {
            "required_arcs": [
                {"volume": 1, "theme": "获得金手指与解除生存初劫"},
                {"volume": 2, "theme": "势力扩张与核心世界观初次揭示"},
            ],
            "forbidden_tropes": ["机械降神", "主角毫无缘由的降智妥协"],
            "must_include_cool_points": [cp.name for cp in cool_points],
            "pacing_milestones": [
                {"chapter_range": "1-3", "event": "开篇黄金三章强钩子呈现"},
                {"chapter_range": "10-15", "event": "第一个主要反派伏诛与首次战利品结算"},
            ],
        }

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        blueprint_id = f"sb_{uuid.uuid4().hex[:12]}"

        return StoryBlueprint(
            schema_version=1,
            id=blueprint_id,
            project_id=project_id,
            title=inputs.get("title", recipe.name if recipe else "未命名灵感故事"),
            revision=1,
            created_at=now_str,
            updated_at=now_str,
            dna=dna,
            selected_atoms=combined_atom_ids,
            selected_recipe_id=recipe_id or "",
            parameters=inputs,
            usp=usp,
            reader_promises=reader_promises,
            pacing=pacing,
            world_constraints=world_constraints,
            character_arcs=character_arcs,
            writing_guide_markdown=writing_guide_md,
            outline_contract=outline_contract,
            review_rules=[
                {
                    "rule_id": "blueprint_ooc_guard",
                    "target": "protagonist",
                    "description": f"主角 {protagonist_name} 的行为必须符合「{protagonist_archetype}」特质，不可无端降智。",
                },
                {
                    "rule_id": "cool_point_cadence",
                    "target": "pacing",
                    "description": "连续5章内必须有阶段性反转或情绪回报，避免过度平淡注水。",
                },
            ],
        )

    def _render_writing_guide(
        self,
        title: str,
        dna: StoryDNA,
        usp: USP,
        recipe: Optional[TropeRecipe],
        reader_promises: list[ReaderPromise],
        pacing: PacingPlan,
    ) -> str:
        mechs_str = "、".join([m.name for m in dna.mechanisms]) or "无特殊外挂（纯智计/苦修）"
        emotions_str = "、".join([e.name for e in dna.emotional_engines]) or "常规逆袭"

        lines = [
            f"# 《{title}》故事创作蓝图与写作指导书",
            "",
            "> 本指南由栖墨「灵感工坊 / Story Blueprint Compiler」根据选定套路原子与故事契约自动编译生成。",
            "> 它作为后续大纲设计 (Outline)、正文生产 (Pipeline) 与质量审校 (Quality Gate) 的结构化指导依据。",
            "",
            "## 一、核心定位与卖点 (USP)",
            f"- **一句话卖点**：{usp.one_sentence_hook}",
            f"- **受众频道**：{dna.channel.label} · 主分类：{dna.genres.primary}",
            f"- **次级标签**：{', '.join(dna.genres.secondary) if dna.genres.secondary else '无'}",
            f"- **核心幻想**：{', '.join(usp.core_fantasy)}",
            "",
            "## 二、十维故事 DNA",
            f"1. **主角设定**：{dna.protagonist.name}（原型：{dna.protagonist.archetype}），动机：{dna.protagonist.core_desire}",
            f"2. **世界结构**：{dna.world.structure}，资源稀缺性：{dna.world.scarcity}",
            f"3. **核心机制 (金手指)**：{mechs_str}",
            f"4. **核心矛盾**：{dna.core_conflict}",
            f"5. **情绪引擎 (爽点)**：{emotions_str}",
            f"6. **叙事结构**：{dna.narrative.structure}，基调：{dna.narrative.style_tone}",
            "",
            "## 三、读者期待承诺 (Reader Promises)",
        ]

        for p in reader_promises:
            lines.append(f"- **[{p.promise_type}]** {p.description}（预期周期：约每 {p.expected_interval} 章兑现一次）")

        lines.extend([
            "",
            "## 四、节奏与分卷排期 (Pacing Plan)",
            f"- **预期总篇幅**：{pacing.target_chapters} 章",
        ])

        for vol in pacing.volumes:
            lines.append(
                f"- **第 {vol.volume_index} 卷**：《{vol.title}》 | 开篇吸引度目标：{vol.opening_hook}/10 | 卷终高潮目标：{vol.climax_target}/10 | 核心爽点：{', '.join(vol.cool_points)}"
            )

        # Mechanism parameters section
        has_custom_params = any(bool(m.parameters) for m in dna.mechanisms)
        if has_custom_params:
            lines.extend([
                "",
                "## 五、金手指参数与运行约束",
            ])
            for m in dna.mechanisms:
                if m.parameters:
                    lines.append(f"### 机制「{m.name}」参数")
                    for k, v in m.parameters.items():
                        lines.append(f"- **{k}**: {v}")

        if recipe and recipe.writing_guide:
            lines.extend([
                "",
                "---",
                "## 附录：套路配方参考指南",
                recipe.writing_guide,
            ])

        return "\n".join(lines)
