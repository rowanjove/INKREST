"""Predefined parameter schemas for major tropes (system, rebirth, transmigration, etc.)."""

from __future__ import annotations

from typing import Any

TROPE_PARAMETER_SCHEMAS: dict[str, dict[str, Any]] = {
    "xitong": {
        "title": "系统流专属参数",
        "description": "定义金手指系统的运行逻辑与交互边界",
        "fields": [
            {
                "key": "consciousness",
                "label": "系统是否有自主意识",
                "type": "boolean",
                "default": False,
                "hint": "false为冰冷面板无实体对话；true为伴生吐槽/引导型智脑",
            },
            {
                "key": "visibility",
                "label": "系统面板可见范围",
                "type": "select",
                "options": ["protagonist_only", "shared_with_chosen", "world_public"],
                "default": "protagonist_only",
                "hint": "绝大多数为仅主角可见；世界公开则演变为全球异变流",
            },
            {
                "key": "reward_source",
                "label": "奖励产出机制",
                "type": "select",
                "options": ["causal_exchange", "kill_drop", "sign_in", "emotion_harvest"],
                "default": "causal_exchange",
                "hint": "因果等价置换、杀怪爆装、日常打卡签到、或吸收他人震惊情绪",
            },
            {
                "key": "mandatory_tasks",
                "label": "是否具备强制惩罚任务",
                "type": "boolean",
                "default": False,
                "hint": "是否由系统发布有失败抹杀危险的任务",
            },
            {
                "key": "growth_decay",
                "label": "成长曲线是否衰减",
                "type": "boolean",
                "default": True,
                "hint": "后期力量膨胀后，系统作用逐渐从依赖转为辅助",
            },
            {
                "key": "origin_reveal",
                "label": "终局是否揭示系统起源",
                "type": "select",
                "options": ["late_story", "never_explain", "ultimate_truth"],
                "default": "late_story",
                "hint": "在大结局阶段解释系统来自高维文明、未来主角自己还是天道残留",
            },
        ],
    },
    "chongsheng": {
        "title": "重生流专属参数",
        "description": "定义重生时间跨度与蝴蝶效应强度",
        "fields": [
            {
                "key": "rebirth_timing",
                "label": "重生回溯节点",
                "type": "select",
                "options": ["youth_era", "critical_turning_point", "disaster_eve"],
                "default": "critical_turning_point",
                "hint": "回到青葱校园少年时、家族覆灭关键前夕、或大劫前三分钟",
            },
            {
                "key": "memory_reliability",
                "label": "前世记忆可靠程度",
                "type": "select",
                "options": ["100_percent_accurate", "gradually_distorted", "partial_amnesia"],
                "default": "100_percent_accurate",
                "hint": "绝对全知先知，或是因为自身改变导致历史发生未知偏差",
            },
            {
                "key": "butterfly_intensity",
                "label": "蝴蝶效应剧烈程度",
                "type": "select",
                "options": ["low", "moderate", "severe"],
                "default": "moderate",
                "hint": "主角微小的改变在第几卷开始彻底打破原有命运轨迹",
            },
            {
                "key": "has_other_reborns",
                "label": "是否存在其他重生者/穿越者",
                "type": "boolean",
                "default": False,
                "hint": "是否产生双重生博弈或敌对反派同样手握先知",
            },
        ],
    },
    "chuanyue": {
        "title": "穿越流专属参数",
        "description": "定义跨界身份与现代知识代差",
        "fields": [
            {
                "key": "transmigration_mode",
                "label": "穿越接入模式",
                "type": "select",
                "options": ["soul_transmigration", "body_transmigration", "reincarnation_baby"],
                "default": "soul_transmigration",
                "hint": "魂穿附身受难者、身穿带现代装备、或是保留宿慧的婴儿转世",
            },
            {
                "key": "tech_dimension_gap",
                "label": "认知/科技代差转化方式",
                "type": "select",
                "options": ["industrial_engineering", "philosophical_insight", "business_model"],
                "default": "industrial_engineering",
                "hint": "靠物理化学工业攀科技、靠唯物辩证降维顿悟道法、或靠商业资本运作",
            },
        ],
    },
    "wuxianliu": {
        "title": "无限流专属参数",
        "description": "定义副本轮回与主空间规则",
        "fields": [
            {
                "key": "instance_type",
                "label": "核心副本形态",
                "type": "select",
                "options": ["horror_rules", "historical_battles", "sci_fi_dungeon", "anime_novels"],
                "default": "horror_rules",
                "hint": "诡异规则怪谈副本、历史重大战争推演、科幻废土、或诸天万界",
            },
            {
                "key": "pvp_allowed",
                "label": "玩家/使徒是否允许内斗互杀",
                "type": "boolean",
                "default": True,
                "hint": "高压弱肉强食环境，或是强制组队一致对外",
            },
            {
                "key": "real_world_bleed",
                "label": "副本能力与异象是否渗透现实",
                "type": "boolean",
                "default": False,
                "hint": "现实世界是否仍为平静日常，或随副本推进逐步超凡复苏",
            },
        ],
    },
}


def get_trope_schema(trope_id: str) -> dict[str, Any] | None:
    return TROPE_PARAMETER_SCHEMAS.get(trope_id)
