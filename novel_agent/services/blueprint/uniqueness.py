"""Novel Uniqueness and Crowdedness Analysis Engine."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class DifferentiationSuggestion(BaseModel):
    category: str  # career | mechanism | protagonist | narrative
    title: str
    advice: str


class UniquenessAnalysisReport(BaseModel):
    commonality_score: int  # 常见度 0-100
    uniqueness_score: int  # 差异度 0-100
    novelty_score: int  # 卖点辨识度 0-100
    crowdedness_score: int  # 赛道拥挤度 0-100
    market_verdict: str
    suggestions: list[DifferentiationSuggestion] = Field(default_factory=list)


class NovelUniquenessEngine:
    """Evaluates narrative novelty and generates actionable anti-cliché differentiation advice."""

    @staticmethod
    def analyze(selected_atom_ids: list[str]) -> UniquenessAnalysisReport:
        selected_set = set(selected_atom_ids)

        # Ultra-common tropes in current web novel market
        cliche_atoms = {"xitong", "dalian", "chongsheng", "zhuangbi"}
        cliche_count = len(selected_set.intersection(cliche_atoms))

        is_ultra_crowded = "xitong" in selected_set and "dalian" in selected_set

        # Compute scores
        if is_ultra_crowded:
            commonality = 88
            crowdedness = 85
            uniqueness = 42
            novelty = 50
            verdict = "套路组合高度成熟且赛道极为拥挤，若无强辨识度设定易沦为常规流水账。"
        elif cliche_count >= 1:
            commonality = 70
            crowdedness = 65
            uniqueness = 62
            novelty = 68
            verdict = "组合兼顾主流阅读快感与创作可行性，建议在金手指代价或主角职业切入点做局部微创新。"
        else:
            commonality = 45
            crowdedness = 40
            uniqueness = 82
            novelty = 85
            verdict = "组合具备很高的独创性与卖点辨识度，需重点关注前三章读者的理解门槛与期待建立。"

        suggestions = [
            DifferentiationSuggestion(
                category="career",
                title="行业 / 职业微创新切入",
                advice="避开千篇一律的杂役弟子或落魄公子，尝试将现代稀缺职业技能（如质检排错、档案修复、心理干预）作为世界规则解析器。",
            ),
            DifferentiationSuggestion(
                category="mechanism",
                title="金手指运行机制反转",
                advice="奖励不再直接赋予力量数值，而是通过因果置换解决具体生态危机；为能力设定具有叙事张力的不可逆代价。",
            ),
            DifferentiationSuggestion(
                category="protagonist",
                title="主角动机与人设立体化",
                advice="主角核心欲望不仅是‘升级逆袭’，增加一件具体的执念（如修补一件长线遗留的遗憾、替旧文明留存火种）。",
            ),
            DifferentiationSuggestion(
                category="narrative",
                title="单元剧与大主线双轮驱动",
                advice="在单调的线性升级中穿插具备独立悬念的小单元，提升每一卷的阅读新鲜度与人物丰满度。",
            ),
        ]

        return UniquenessAnalysisReport(
            commonality_score=commonality,
            uniqueness_score=uniqueness,
            novelty_score=novelty,
            crowdedness_score=crowdedness,
            market_verdict=verdict,
            suggestions=suggestions,
        )
