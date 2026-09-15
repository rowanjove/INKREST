"""10-Agent Orchestrator for Script Murder generation pipeline."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from ..schemas import (
    CharacterKnowledgeItem,
    CharacterProfile,
    CharacterTimelineEvent,
    ClueItem,
    DeductiveConclusion,
    GameFlow,
    GameRound,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)
from ..services.model_service import ModelService


class ScriptMurderOrchestrator:
    """Coordinates the 10 specialized agents with strict visibility isolation."""

    def __init__(self, model_service: ModelService):
        self.model_svc = model_service

    # -----------------------------------------------------------------------
    # 1. Chief Designer: Brief Generation
    # -----------------------------------------------------------------------
    def generate_brief(self, inspiration: str, player_count: int = 6) -> Dict[str, Any]:
        system_prompt = self.model_svc.build_system_prompt("chief_designer")
        user_prompt = (
            f"请根据创作者灵感构思一个剧本杀企划大纲：\n"
            f"灵感：{inspiration}\n"
            f"人数：{player_count} 人\n"
            f"请给出包含 title, genre, era, setting, core_conflict, atmosphere 的设计简报。"
        )
        raw_text = self.model_svc.generate_text("chief_designer", system_prompt, user_prompt)
        try:
            return self.model_svc.extract_json(raw_text)
        except Exception:
            if not self.model_svc.offline_mode:
                raise
            return {
                "title": "雾港十三号",
                "genre": ["本格推理", "社会派"],
                "era": "1998年",
                "setting": "北方海港保税区",
                "core_conflict": "走私货单与封口费纠纷导致的密闭仓库命案",
                "atmosphere": "暴雨、锈蚀金属、柴油味、冷峻压抑",
            }

    # -----------------------------------------------------------------------
    # 2. Truth Architect: Canonical Truth Generation
    # -----------------------------------------------------------------------
    def generate_truth_canon(self, inspiration: str, player_count: int = 6) -> TruthCanon:
        system_prompt = self.model_svc.build_system_prompt("truth_architect")
        user_prompt = (
            f"创作背景与灵感：{inspiration}\n"
            f"要求：构建一个严格遵循物理与人体常理的 Truth Canon。\n"
            f"必须明确 victim (受害者), killer (真凶代号 CHAR_02), cause_of_death (死因), "
            f"crime_time_window (案发时间窗口元组), crime_scene (现场), crime_method (手法), "
            f"true_motive (真实动机), 以及至少 2-4 条原子级客观事实 facts (带稳定 F001 等 ID)。"
        )
        return self.model_svc.generate_structured(
            role="truth_architect",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=TruthCanon,
        )

    # -----------------------------------------------------------------------
    # 3. Character Architect: Cast & Epistemic Boundaries
    # -----------------------------------------------------------------------
    def generate_characters(self, canon: TruthCanon, player_count: int = 6) -> List[CharacterProfile]:
        class CastContainer(BaseModel):
            characters: List[CharacterProfile]

        system_prompt = self.model_svc.build_system_prompt("character_architect")
        user_prompt = (
            f"根据以下 Truth Canon 构思 {player_count} 名嫌疑人角色卡：\n"
            f"受害者：{canon.victim}\n"
            f"真凶 ID：{canon.killer}\n"
            f"案发窗口：{canon.crime_time_window[0]} ~ {canon.crime_time_window[1]}\n"
            f"第一现场：{canon.crime_scene}\n"
            f"已知事实：{json.dumps([f.model_dump() for f in canon.facts], ensure_ascii=False)}\n\n"
            f"【要求】\n"
            f"1. 必须生成恰好 {player_count} 名角色，ID 依次为 CHAR_01, CHAR_02, ...\n"
            f"2. 角色之间的动机必须具有多向度差异（欠债、情感、旧怨、销毁伪证等），拒绝全员同一款秘密。\n"
            f"3. 严格设置 knowledge_map，区分真实经历、主观相信与主动谎言。"
        )

        try:
            container = self.model_svc.generate_structured(
                role="character_architect",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CastContainer,
            )
            return container.characters[:player_count]
        except Exception:
            if not self.model_svc.offline_mode:
                raise
            # Deterministic fallback cast
            killer_id = canon.killer or "CHAR_02"
            results = []
            roles_demo = [
                ("CHAR_01", "林晚", "女", 26, "独立调查记者", "追查十年前沉船索赔内幕"),
                (killer_id, "周野", "男", 31, "货代外勤组长", "因盗卖提货单被受害者敲诈，动杀心"),
                ("CHAR_03", "孙潇", "男", 45, "港区安保队长", "私开闸口收受好处，案发时脱岗"),
                ("CHAR_04", "赵启", "男", 38, "航运公司法务", "协助隐匿账本，曾与死者激烈争执"),
                ("CHAR_05", "苏曼", "女", 29, "保税冷库化验员", "曾发现毒物与药品缺失却未上报"),
                ("CHAR_06", "韩峰", "男", 52, "远洋老水手长", "死者生前债权人，当晚持借条上门"),
            ]
            for cid, name, gender, age, identity, secret in roles_demo[:player_count]:
                is_k = (cid == killer_id)
                results.append(
                    CharacterProfile(
                        id=cid,
                        name=name,
                        gender=gender,
                        age=age,
                        public_identity=identity,
                        desire="掩盖自身不可告人的利益污点并自保",
                        secrets=[secret],
                        timeline=[
                            CharacterTimelineEvent(
                                time="21:15",
                                location=canon.crime_scene if is_k else "值班室",
                                activity_real="在现场触发延时配重机关" if is_k else "在抽烟避雨",
                                activity_claimed="在宿舍休息",
                            )
                        ],
                        knowledge_map=[
                            CharacterKnowledgeItem(
                                fact_id=canon.facts[0].id if canon.facts else "F001",
                                epistemic_state="knowledge" if is_k else "lie",
                                narrative_statement="亲身经历作案全过程" if is_k else "声称毫不知情",
                                allowed_to_reveal=not is_k,
                            )
                        ],
                    )
                )
            return results

    # -----------------------------------------------------------------------
    # 4. Clue Engineer: Deductive Clue DAG
    # -----------------------------------------------------------------------
    def generate_clue_graph(
        self, canon: TruthCanon, characters: List[CharacterProfile]
    ) -> Tuple[List[ClueItem], List[DeductiveConclusion]]:
        class ClueGraphContainer(BaseModel):
            clues: List[ClueItem]
            conclusions: List[DeductiveConclusion]

        system_prompt = self.model_svc.build_system_prompt("clue_engineer")
        user_prompt = (
            f"根据以下案情生成法医勘验与现场物证 DAG：\n"
            f"受害者：{canon.victim}，死因：{canon.cause_of_death}，现场：{canon.crime_scene}\n"
            f"真凶：{canon.killer}，手法：{canon.crime_method}\n"
            f"事实列表：{json.dumps([f.model_dump() for f in canon.facts], ensure_ascii=False)}\n\n"
            f"【要求】\n"
            f"1. 生成至少 4-6 条物证 (ClueItem)，必须冷冰冰法医体，描述物理残损、尺寸与残留物，绝不带剧透引导。\n"
            f"2. 包含至少 1 条合理的误导项 (is_red_herring=True) 及其澄清线索引用。\n"
            f"3. 生成至少 1-2 条关键推论 (DeductiveConclusion)，并以 supported_by_clues 闭环锁定。"
        )

        try:
            container = self.model_svc.generate_structured(
                role="clue_engineer",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=ClueGraphContainer,
            )
            return container.clues, container.conclusions
        except Exception:
            if not self.model_svc.offline_mode:
                raise
            c1 = ClueItem(
                id="C001",
                title="沾有工业黄油的断裂尼龙绳",
                content="8毫米多股编织尼龙绳，断口具明显机械拉伸撕裂痕迹，绳结内嵌少量润滑油脂。",
                round=1,
                location=canon.crime_scene,
                fact_refs=[f.id for f in canon.facts[:1]],
                supports_conclusions=["CONCL_01"],
            )
            c2 = ClueItem(
                id="C002",
                title="西门逃生门槛带血纤维",
                content="西安全门铁质凸起处刮蹭留存深蓝高密尼龙布料丝线，伴两处附着性血斑，化验为B型血。",
                round=2,
                location="西侧安全通道",
                fact_refs=[f.id for f in canon.facts[1:2]] if len(canon.facts) > 1 else [],
                supports_conclusions=["CONCL_01"],
            )
            concl = DeductiveConclusion(
                id="CONCL_01",
                title="真凶通过西侧通道逃逸并负伤",
                description="凶手在21:16前后通过西安全门逃离，右膝留有撕裂性伤口并具有B型血特征。",
                supported_by_clues=["C001", "C002"],
                target_suspect_id=canon.killer,
            )
            return [c1, c2], [concl]

    # -----------------------------------------------------------------------
    # 5. Flow Director: Rounds & Pacing
    # -----------------------------------------------------------------------
    def generate_game_flow(
        self, canon: TruthCanon, characters: List[CharacterProfile], clues: List[ClueItem]
    ) -> GameFlow:
        system_prompt = self.model_svc.build_system_prompt("flow_director")
        user_prompt = (
            f"根据案情编排 3 轮递进式搜证与讨论流程：\n"
            f"受害人：{canon.victim}，真凶：{canon.killer}\n"
            f"现有物证总数：{len(clues)} 条。\n"
            f"请输出完整的 GameFlow JSON，包含 prologue, rounds (round 1~3), epilogue。"
        )
        try:
            return self.model_svc.generate_structured(
                role="flow_director",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=GameFlow,
            )
        except Exception:
            if not self.model_svc.offline_mode:
                raise
            return GameFlow(
                prologue="1998年深秋暴雨，北方海港保税仓库突发命案，仓管主任陈默倒在血泊之中，港区大门已被巡警封锁。",
                rounds=[
                    GameRound(
                        round_index=1,
                        title="第一轮：身份核验与初始搜证",
                        stage_objective="阐述各人案发前轨迹，调查现场浅表物证",
                        search_clue_ids=[c.id for c in clues if c.round == 1],
                        public_events=["受害人陈默遗体被保安孙潇发现并报告"],
                        discussion_minutes=45,
                    ),
                    GameRound(
                        round_index=2,
                        title="第二轮：深水区物证与时间线对质",
                        stage_objective="搜寻关键机械与生理痕迹，排查不在场证明谎言",
                        search_clue_ids=[c.id for c in clues if c.round == 2],
                        public_events=["法医初步尸温与血迹化验单下发"],
                        discussion_minutes=60,
                    ),
                    GameRound(
                        round_index=3,
                        title="第三轮：排他性辩论与最终决选",
                        stage_objective="锁定致命机关部署者，指认真凶并投票",
                        vote_required=True,
                        discussion_minutes=30,
                    ),
                ],
                epilogue_killer="真相大白，真凶在铁证如山下瘫软在地，承认了因走私提单败露而动杀机的全部罪行。",
                epilogue_escape="真凶成功误导全场，带着伪造的离港签证消失在漆黑的风雨海港之中。",
            )

    # -----------------------------------------------------------------------
    # 6. Script Writer: Visibility Filtered Character Script
    # -----------------------------------------------------------------------
    def generate_character_script(
        self,
        character: CharacterProfile,
        canon: TruthCanon,
        act: int = 1,
    ) -> str:
        """Enforces Strict Visibility Filter before dispatching to script_writer."""
        # 1. Physical visibility isolation filter
        known_fact_ids = {km.fact_id for km in character.knowledge_map}
        allowed_facts = [f for f in canon.facts if f.id in known_fact_ids]

        # 2. Build isolated context
        context_block = {
            "your_name": character.name,
            "your_identity": character.public_identity,
            "your_secret": character.secrets,
            "your_desire": character.desire,
            "your_timeline": [
                {"time": ev.time, "real": ev.activity_real, "claimed": ev.activity_claimed}
                for ev in character.timeline
            ],
            "what_you_know_as_truth": [
                {"fact": f.title, "statement": f.content} for f in allowed_facts
            ],
        }

        system_prompt = self.model_svc.build_system_prompt("script_writer")
        user_prompt = (
            f"请为角色【{character.name}】撰写【第 {act} 幕】玩家个人剧本。\n\n"
            f"【你的严格知识边界（你只知道以下内容，超出部分严禁描写或提及）】\n"
            f"{json.dumps(context_block, ensure_ascii=False, indent=2)}\n\n"
            f"【致命规则】\n"
            f"1. 绝不使用形容词定性心理（不写‘你很紧张’，只写‘你手心冒汗’、‘门轴响时后背发凉’）。\n"
            f"2. 语言必须带市井与职业呼吸感，充满生活对话的停顿与回避。\n"
            f"3. 严禁使用任何 AI 常见套话（命运的齿轮、殊不知、耐人寻味等）。"
        )

        return self.model_svc.generate_text("script_writer", system_prompt, user_prompt)

    # -----------------------------------------------------------------------
    # 7. Host Writer: Master Manual
    # -----------------------------------------------------------------------
    def generate_host_guide(self, workspace: ScriptMurderWorkspace) -> str:
        system_prompt = self.model_svc.build_system_prompt("host_writer")
        summary = {
            "victim": workspace.canon.victim,
            "killer": workspace.canon.killer,
            "crime_scene": workspace.canon.crime_scene,
            "crime_method": workspace.canon.crime_method,
            "true_motive": workspace.canon.true_motive,
            "facts": [f.model_dump() for f in workspace.canon.facts],
            "clues": [c.model_dump() for c in workspace.clues],
            "characters": [{"id": c.id, "name": c.name, "secrets": c.secrets} for c in workspace.characters],
        }

        user_prompt = (
            f"请为主持人编写全知视角的【主持人复盘与实操手册】。\n"
            f"完整案情事实如下：\n"
            f"{json.dumps(summary, ensure_ascii=False, indent=2)}\n\n"
            f"请包含：\n"
            f"1. 案情完整真相白皮书\n"
            f"2. 凶手作案真实时间线与失误破绽\n"
            f"3. 核心物证解析与三级阶梯扶车指引\n"
            f"4. 终局投票与复盘讲稿"
        )
        return self.model_svc.generate_text("host_writer", system_prompt, user_prompt)
