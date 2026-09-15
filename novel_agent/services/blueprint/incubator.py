"""Snowflake-style progressive inspiration incubator."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class IncubatedSeed(BaseModel):
    id: str
    direction_title: str
    summary: str
    channel: str = "male"
    primary_genre: str
    mechanisms: list[str] = Field(default_factory=list)
    cool_points: list[str] = Field(default_factory=list)
    protagonist_name: str
    protagonist_archetype: str
    core_desire: str
    world_structure: str
    hook: str


class IncubateResult(BaseModel):
    original_idea: str
    seeds: list[IncubatedSeed] = Field(default_factory=list)


class InspirationIncubator:
    """Derives multi-angle structured story seeds from a single free-form brainstorm idea."""

    @staticmethod
    def incubate(idea_text: str) -> IncubateResult:
        cleaned = idea_text.strip()
        if not cleaned:
            cleaned = "普通主角在特殊世界利用特别规则破局"

        # Rule-based / deterministic heuristic derivations based on keywords
        is_scifi = any(k in cleaned for k in ["科技", "现代", "机房", "算力", "芯片", "工程师", "代码", "AI", "赛博"])
        is_xianxia = any(k in cleaned for k in ["修仙", "灵根", "宗门", "飞升", "道法", "真仙", "魔道"])
        is_history = any(k in cleaned for k in ["古代", "大秦", "大唐", "三国", "皇朝", "工业革命", "封建"])
        is_mystery = any(k in cleaned for k in ["规则", "怪谈", "诡异", "死亡", "倒计时", "案", "悬疑"])

        primary_genre = "科幻" if is_scifi else ("仙侠" if is_xianxia else ("历史" if is_history else ("悬疑" if is_mystery else "玄幻")))

        # Seed A: 工业降维与秩序重塑
        seed_a = IncubatedSeed(
            id="dir_order_reform",
            direction_title="方向 A：技术降维与文明秩序重构",
            summary=f"立足「{cleaned[:30]}...」，主角将现代知识与异界规则系统化融合，形成代差碾压。",
            channel="male",
            primary_genre=primary_genre,
            mechanisms=["xitong", "chuanyue"] if is_scifi or is_xianxia else ["majia"],
            cool_points=["dalian", "shengji"],
            protagonist_name="顾衍",
            protagonist_archetype="冷静理性的技术流执行者",
            core_desire="以精密规则打破旧体制资源垄断，重建绝对掌控权",
            world_structure="陈旧固化、等级森严的垄断型社会结构",
            hook=f"手握不可替代的底层法则理解，面对势不可挡的庞然大物，主角用降维体系撕开整个世界的裂痕。",
        )

        # Seed B: 稳健经营与幕后执子
        seed_b = IncubatedSeed(
            id="dir_behind_scenes",
            direction_title="方向 B：稳健苟道与幕后经营借力",
            summary="主角隐于幕后，利用信息差构建庞大隐秘组织，步步为营以小博大。",
            channel="male",
            primary_genre=primary_genre,
            mechanisms=["chongsheng", "majia"] if is_xianxia else ["jingying"],
            cool_points=["fuchou", "dalian"],
            protagonist_name="沈默",
            protagonist_archetype="城府极深的稳健幕后执棋者",
            core_desire="在各方暗流交错的险局中苟全性命，暗中织网掌控全局",
            world_structure="多方巨头博弈、杀机暗藏的混乱多极势力格局",
            hook=f"全天下以为他只是个微不足道的棋子，直到大幕落下，各方才惊觉所有人都在他的棋局之中。",
        )

        # Seed C: 因果回档与解谜推演
        seed_c = IncubatedSeed(
            id="dir_causal_simulator",
            direction_title="方向 C：无限回档与命运因果推演",
            summary="通过机制不断模拟未来轨迹，试错排除死局，在绝境中寻找唯一生机。",
            channel="male" if not is_mystery else "general",
            primary_genre=primary_genre,
            mechanisms=["chongsheng", "wuxianliu"] if is_mystery or is_xianxia else ["xitong"],
            cool_points=["shengcun", "jiushu"],
            protagonist_name="林策",
            protagonist_archetype="绝境不屈的因果推演者",
            core_desire="探寻世界最深层的终极真相，拯救必将倾覆的既定宿命",
            world_structure="充满未知禁忌与不可名状因果纠缠的世界",
            hook=f"当所有人都在走向注定的覆灭时，唯有他洞悉了所有死亡路径，在最狭窄的绝境中破茧而出。",
        )

        return IncubateResult(
            original_idea=cleaned,
            seeds=[seed_a, seed_b, seed_c],
        )
