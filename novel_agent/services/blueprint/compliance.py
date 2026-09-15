"""Compliance checker between Story Blueprint constraints and chapter/outline drafts."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from novel_agent.domain.blueprint.blueprint import StoryBlueprint


class ComplianceViolation(BaseModel):
    rule_id: str
    severity: str  # error | warning
    category: str  # ooc | world_rule | promise_delayed
    target: str
    message: str
    suggestion: str = ""


class ComplianceReport(BaseModel):
    is_compliant: bool = True
    violations: list[ComplianceViolation] = Field(default_factory=list)
    compliance_score: int = 100


class BlueprintComplianceChecker:
    """Audits narrative drafts, outlines, and chapter texts against Story Blueprint contracts."""

    @staticmethod
    def audit_draft(
        blueprint: StoryBlueprint,
        draft_summary: str,
        current_chapter_index: int = 1,
        last_payoff_chapter: int = 1,
    ) -> ComplianceReport:
        violations: list[ComplianceViolation] = []

        # 1. Check Reader Promise interval delays
        for promise in blueprint.reader_promises:
            try:
                # e.g. "3-5" -> max is 5
                parts = [int(p.strip()) for p in promise.expected_interval.split("-") if p.strip().isdigit()]
                max_interval = max(parts) if parts else 8
            except Exception:
                max_interval = 8

            chapters_since_payoff = max(0, current_chapter_index - last_payoff_chapter)
            if chapters_since_payoff > max_interval:
                violations.append(
                    ComplianceViolation(
                        rule_id=f"promise_delay_{promise.id}",
                        severity="warning",
                        category="promise_delayed",
                        target=promise.promise_type,
                        message=f"读者期待承诺「{promise.description}」已连续 {chapters_since_payoff} 章未兑现（约定推进周期上限为 {max_interval} 章）。",
                        suggestion="建议在本章或临近章节推进对应的高潮或回报结算，保持阅读张力。",
                    )
                )

        # 2. Check World Rule Constraints
        for constraint in (blueprint.world_constraints or []):
            for forbidden_item in (constraint.forbidden or []):
                if forbidden_item and forbidden_item in draft_summary:
                    violations.append(
                        ComplianceViolation(
                            rule_id=f"world_rule_{constraint.name}",
                            severity="error",
                            category="world_rule",
                            target=constraint.name,
                            message=f"剧情可能触碰世界设定约束：出现了限制设定「{forbidden_item}」。",
                            suggestion=f"设定惩罚机制为：{', '.join(constraint.consequences) or '世界秩序反噬'}，请核对是否符合设定要求。",
                        )
                    )

        # 3. Check Protagonist OOC tendencies
        protagonist = getattr(getattr(blueprint, "dna", None), "protagonist", None)
        if protagonist and protagonist.archetype:
            if "无脑" in draft_summary or "冲动鲁莽" in draft_summary:
                if "谨慎" in protagonist.archetype or "稳健" in protagonist.archetype:
                    violations.append(
                        ComplianceViolation(
                            rule_id="ooc_prudence",
                            severity="warning",
                            category="ooc",
                            target=protagonist.name or "主角",
                            message=f"主角行为可能出现人设偏差：设定为「{protagonist.archetype}」，但剧情概况中体现出鲁莽冲动倾向。",
                            suggestion="建议调整决策动机，让行动符合主角的核心性格逻辑。",
                        )
                    )

        has_errors = any(v.severity == "error" for v in violations)
        score = 100 - (len([v for v in violations if v.severity == "error"]) * 30) - (len([v for v in violations if v.severity == "warning"]) * 15)
        score = max(0, min(100, score))

        return ComplianceReport(
            is_compliant=not has_errors,
            violations=violations,
            compliance_score=score,
        )
