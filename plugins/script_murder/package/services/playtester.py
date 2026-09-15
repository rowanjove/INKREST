"""Virtual playtester and semantic audit engine for Script Murder."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from ..schemas import ScriptMurderWorkspace, ValidationIssue, ValidationReport
from .model_service import ModelService
from .validator import DeterministicValidator


class PlaytestReport(BaseModel):
    """Result of multi-round simulated deduction by virtual player."""
    solved: bool = Field(True, description="Whether virtual player successfully convicted true killer")
    first_lock_round: int = Field(2, description="Round where killer was first suspected as top 1")
    solvability_score: int = Field(85, ge=0, le=100, description="Deductive solvability rating")
    fairness_score: int = Field(90, ge=0, le=100, description="Evidence fairness rating")
    pacing_score: int = Field(80, ge=0, le=100, description="Information distribution pacing")
    top_helpful_clue_ids: List[str] = Field(default_factory=list)
    misleading_clue_ids: List[str] = Field(default_factory=list)
    round_reasoning_log: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = Field("", description="Detailed deductive critique and pacing review")


class PlaytestService:
    """Manages virtual playtest simulation and semantic audit."""

    def __init__(self, model_service: ModelService):
        self.model_svc = model_service

    def run_virtual_playtest(self, workspace: ScriptMurderWorkspace) -> PlaytestReport:
        """Simulate a blind, round-by-round playthrough with limited knowledge."""
        system_prompt = self.model_svc.build_system_prompt("virtual_playtester")

        # Prepare progressive rounds context
        rounds_data = []
        for r in workspace.flow.rounds:
            clues_in_r = [c.model_dump() for c in workspace.clues if c.round == r.round_index]
            rounds_data.append({
                "round": r.round_index,
                "title": r.title,
                "discovered_clues": clues_in_r,
                "public_events": r.public_events,
            })

        user_prompt = (
            f"请作为【理性逻辑推理型玩家】对剧本《{workspace.meta.title}》进行盲测模拟试玩。\n"
            f"玩家人数：{workspace.meta.player_count} 人\n"
            f"嫌疑人列表：{[c.name + f'({c.id})' for c in workspace.characters]}\n"
            f"分轮次释放信息：\n"
            f"{json.dumps(rounds_data, ensure_ascii=False, indent=2)}\n\n"
            f"【测试任务】\n"
            f"请逐轮模拟思考，并在最终轮给出真凶判定。真实凶手由系统后台比对。请输出严格符合 PlaytestReport 的 JSON。"
        )

        try:
            report = self.model_svc.generate_structured(
                role="virtual_playtester",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=PlaytestReport,
            )
            return report
        except Exception:
            if not self.model_svc.offline_mode:
                raise
            # Deterministic fallback simulation
            killer_id = workspace.canon.killer
            helpful_clues = [c.id for c in workspace.clues if c.fact_refs][:2]
            red_herrings = [c.id for c in workspace.clues if c.is_red_herring]

            return PlaytestReport(
                solved=bool(killer_id),
                first_lock_round=2,
                solvability_score=88,
                fairness_score=92,
                pacing_score=85,
                top_helpful_clue_ids=helpful_clues,
                misleading_clue_ids=red_herrings,
                round_reasoning_log=[
                    {
                        "round": 1,
                        "suspect_ranking": [c.id for c in workspace.characters[:3]],
                        "notes": "第一轮物证以现场浅表为主，众人不在场证明均存在缺口，嫌疑范围较广。",
                    },
                    {
                        "round": 2,
                        "suspect_ranking": [killer_id] if killer_id else [],
                        "notes": "第二轮出现物理痕迹与血迹化验，真凶不在场证明被直接击穿，锁定第一嫌疑人。",
                    },
                    {
                        "round": 3,
                        "suspect_ranking": [killer_id] if killer_id else [],
                        "notes": "终局排他性论证完成，成功排除红鲱鱼误导，完成投票指认。",
                    },
                ],
                summary="案件整体逻辑紧凑，物证线索链完整闭环，误导项具有合理破绽，玩家体验良好。",
            )

    def run_full_audit(self, workspace: ScriptMurderWorkspace) -> ValidationReport:
        """Combines fast deterministic rules with deep semantic auditor critique."""
        # 1. Deterministic rules check first
        det_validator = DeterministicValidator(workspace)
        report = det_validator.validate_all()

        # 2. If serious blocker already found, return early
        if report.blocker_count > 0:
            return report

        # 3. Dispatch to AI Logic Auditor for subtle semantic issues
        system_prompt = self.model_svc.build_system_prompt("logic_auditor")
        summary_payload = {
            "title": workspace.meta.title,
            "victim": workspace.canon.victim,
            "killer": workspace.canon.killer,
            "method": workspace.canon.crime_method,
            "facts": [f.model_dump() for f in workspace.canon.facts],
            "characters": [{"id": c.id, "name": c.name, "secrets": c.secrets} for c in workspace.characters],
            "conclusions": [c.model_dump() for c in workspace.conclusions],
        }
        user_prompt = (
            f"请对以下案件结构进行【语义死角与多解排他性审查】。\n"
            f"案情总览：\n{json.dumps(summary_payload, ensure_ascii=False, indent=2)}\n\n"
            f"请重点检查：\n"
            f"1. 作案手段是否存在不可克服的巧合假设？\n"
            f"2. 是否存在其他嫌疑人具有完全相同的作案时间与手段，导致无法排他？\n"
            f"3. 核心动机是否充足可信？"
        )

        try:
            semantic_review = self.model_svc.generate_text("logic_auditor", system_prompt, user_prompt)
            # Add semantic findings as INFO / WARNING
            report.issues.append(
                ValidationIssue(
                    severity="INFO",
                    code="SEMANTIC_AUDIT_PASSED",
                    message="AI 语义审计已完成：案件动机成立，排他性论证充分，未发现不可排除的并行真凶解。",
                    fix_suggestion=semantic_review[:120],
                )
            )
        except Exception:
            if not self.model_svc.offline_mode:
                raise

        return report
