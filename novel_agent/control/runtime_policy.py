"""Unified runtime policy from outline scale_profile + pipeline.yaml."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from novel_agent.control.scale_profile import (
    SCALE_PROFILES,
    is_vector_enabled_for_project,
    load_outline_scale_profile,
    resolve_scale_profile,
)

PLANNING_MODE_HINTS: Dict[str, str] = {
    "single_shot": "微型短篇：场景宜少而精（通常 1–2 场），单线推进，避免支线铺陈。",
    "full_upfront": "短篇：结构紧凑，场景数适中（通常 2–4 场），伏笔宜在本章内可收束。",
    "rolling_window": "中长篇：可按滚动窗口规划，注意与宏观大纲及叙事债务对齐。",
    "dynamic_volume": "长篇：注意卷/篇章节奏，场景可略多但需服务主线推进。",
    "fractal_dynamic_volume": "超长篇：分形卷结构，本章聚焦当前卷目标，避免抢戏。",
    "container_episode": "连载：本章服务于当前「集」目标，结尾保留钩子。",
}

MAX_PLAN_SCENES_BY_SCALE: Dict[str, int] = {
    "micro": 2,
    "short": 4,
    "medium": 8,
    "long": 10,
    "epic": 12,
    "infinite": 12,
}

# economy | standard | premium — drives audit sub-steps and persona cost
PIPELINE_TIER_BY_SCALE: Dict[str, str] = {
    "micro": "economy",
    "short": "economy",
    "medium": "standard",
    "long": "standard",
    "epic": "premium",
    "infinite": "premium",
}

AUDIT_PROFILE_BY_TIER: Dict[str, Dict[str, Any]] = {
    "economy": {
        "skip_continuity": True,
        "skip_chapter_summary": False,
        "max_rewrites_override": 0,
    },
    "standard": {
        "skip_continuity": False,
        "skip_chapter_summary": False,
        "max_rewrites_override": None,
    },
    "premium": {
        "skip_continuity": False,
        "skip_chapter_summary": False,
        "max_rewrites_override": None,
    },
}


def merge_scale_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing scale_profile fields from canonical SCALE_PROFILES defaults."""
    scale = str(profile.get("scale") or "medium")
    base = deepcopy(SCALE_PROFILES.get(scale, SCALE_PROFILES["medium"]))
    return {**base, **profile}


def is_semantic_search_effective(root_dir: Path) -> bool:
    """True when vector recall can use a non-stub embedding provider."""
    if not is_vector_enabled_for_project(root_dir):
        return False
    from novel_agent.pipeline import load_pipeline_settings

    emb = load_pipeline_settings(root_dir).get("embedding", {}) or {}
    provider = str(emb.get("provider") or "stub").strip().lower()
    return provider != "stub"


def goal_fingerprint(goal: str) -> str:
    return hashlib.sha256((goal or "").strip().encode("utf-8")).hexdigest()[:16]


def should_skip_chapter_planner(
    checkpoint: Dict[str, Any],
    completed_stages: List[str],
    goal_fp: str,
    plan: Dict[str, Any],
) -> Tuple[bool, str]:
    """Whether to reuse plan.json without calling the planner LLM."""
    if checkpoint.get("goal_hash") != goal_fp:
        return False, "goal_changed"
    if not plan:
        return False, "empty_plan"
    stored_plan_hash = checkpoint.get("plan_hash")
    if stored_plan_hash:
        current = plan_fingerprint(plan)
        if current != stored_plan_hash:
            return False, "plan_hash_mismatch"
    last_stage = str(checkpoint.get("last_stage") or "")
    resumable = str(checkpoint.get("resumable_from") or "")
    if "generation" in completed_stages:
        return True, "resume_from_checkpoint"
    if last_stage in ("quality_blocked", "approval_rejected") or resumable in (
        "audit",
        "generation",
    ):
        if "planner" in completed_stages or stored_plan_hash:
            return True, "resume_after_gate_without_replan"
    return False, "planner_required"


def plan_fingerprint(plan: Dict[str, Any]) -> str:
    import json

    payload = json.dumps(
        {
            "chapter_goal": plan.get("chapter_goal") or plan.get("chapter_title"),
            "scenes": [
                {"scene_id": s.get("scene_id"), "purpose": s.get("purpose")}
                for s in (plan.get("scenes") or [])
                if isinstance(s, dict)
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RuntimePolicy:
    scale: str
    planning_mode: str
    vector_enabled: bool
    semantic_search_effective: bool
    max_plan_scenes: int
    label: str = ""
    outline_layers: Tuple[str, ...] = ()
    planning_window: int = 0
    calibration_interval: int = 0
    target_chapters: int = 0
    pipeline_tier: str = "standard"
    audit_profile: str = "standard"

    def planning_hint(self) -> str:
        return PLANNING_MODE_HINTS.get(
            self.planning_mode,
            PLANNING_MODE_HINTS["rolling_window"],
        )


def resolve_pipeline_tier(root_dir: Path, scale: str) -> str:
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = str(runtime.get("pipeline_tier") or "").strip().lower()
    if raw in ("economy", "standard", "premium"):
        return raw
    return PIPELINE_TIER_BY_SCALE.get(scale, "standard")


def resolve_audit_profile(root_dir: Path, pipeline_tier: str) -> str:
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    raw = str(runtime.get("audit_profile") or "").strip().lower()
    if raw in AUDIT_PROFILE_BY_TIER:
        return raw
    return pipeline_tier if pipeline_tier in AUDIT_PROFILE_BY_TIER else "standard"


def get_audit_profile_flags(root_dir: Path) -> Dict[str, Any]:
    policy = resolve_runtime_policy(root_dir)
    base = dict(AUDIT_PROFILE_BY_TIER.get(policy.audit_profile, AUDIT_PROFILE_BY_TIER["standard"]))
    from novel_agent.pipeline import load_pipeline_settings

    runtime = load_pipeline_settings(root_dir).get("runtime", {}) or {}
    overrides = runtime.get("audit_profile_overrides") or {}
    if isinstance(overrides, dict):
        base.update({k: v for k, v in overrides.items() if k in base})
    return base


def resolve_runtime_policy(root_dir: Path) -> RuntimePolicy:
    raw = load_outline_scale_profile(root_dir)
    if raw is None:
        profile = resolve_scale_profile(target_chapters=20)
    else:
        profile = merge_scale_profile(raw)
    scale = str(profile.get("scale") or "medium")
    tier = resolve_pipeline_tier(root_dir, scale)
    audit_profile = resolve_audit_profile(root_dir, tier)
    return RuntimePolicy(
        scale=scale,
        planning_mode=str(profile.get("planning_mode") or "rolling_window"),
        vector_enabled=is_vector_enabled_for_project(root_dir),
        semantic_search_effective=is_semantic_search_effective(root_dir),
        max_plan_scenes=int(
            profile.get("max_plan_scenes") or MAX_PLAN_SCENES_BY_SCALE.get(scale, 8)
        ),
        label=str(profile.get("label") or ""),
        outline_layers=tuple(profile.get("outline_layers") or ()),
        planning_window=int(profile.get("planning_window") or 0),
        calibration_interval=int(profile.get("calibration_interval") or 0),
        target_chapters=int(profile.get("target_chapters") or profile.get("max_chapters") or 0),
        pipeline_tier=tier,
        audit_profile=audit_profile,
    )


def format_runtime_context_for_planner(policy: RuntimePolicy) -> str:
    layers = ", ".join(policy.outline_layers) if policy.outline_layers else "（按档位默认）"
    lines = [
        f"体量档位: {policy.label or policy.scale} ({policy.scale})",
        f"规划模式: {policy.planning_mode}",
        policy.planning_hint(),
        f"大纲层级: {layers}",
        f"场景数量上限: {policy.max_plan_scenes}",
    ]
    if policy.planning_window > 0:
        lines.append(f"滚动规划窗口: 最近 {policy.planning_window} 章")
    if policy.calibration_interval > 0:
        lines.append(f"长篇校准间隔: 每 {policy.calibration_interval} 章")
    if not policy.semantic_search_effective:
        lines.append(
            "【重要】语义向量未生效（Embedding 为 stub 或未配置 API）："
            "跨章剧情去重、向量伏笔召回均不可用；勿在规划中假设「语义检索已命中」。"
            "SQLite 叙事债务与规则类伏笔提示仍可用。请在项目配置中启用真实 Embedding。"
        )
    elif not policy.vector_enabled:
        lines.append(
            "当前体量档位关闭向量能力：勿依赖跨章语义去重（SQLite 债务提示仍可用）。"
        )
    return "\n".join(lines)


def format_scale_profile_for_chief_editor(profile: Dict[str, Any]) -> str:
    """Macro outline constraints from scale_profile (used before outline.json exists)."""
    merged = merge_scale_profile(profile)
    policy = RuntimePolicy(
        scale=str(merged.get("scale") or "medium"),
        planning_mode=str(merged.get("planning_mode") or "rolling_window"),
        vector_enabled=bool(merged.get("vector_enabled", True)),
        semantic_search_effective=bool(merged.get("vector_enabled", True)),
        max_plan_scenes=int(
            merged.get("max_plan_scenes")
            or MAX_PLAN_SCENES_BY_SCALE.get(str(merged.get("scale") or "medium"), 8)
        ),
        label=str(merged.get("label") or ""),
        outline_layers=tuple(merged.get("outline_layers") or ()),
        planning_window=int(merged.get("planning_window") or 0),
        calibration_interval=int(merged.get("calibration_interval") or 0),
        target_chapters=int(merged.get("target_chapters") or merged.get("max_chapters") or 0),
    )
    lines = [
        "## 体量架构约束（必须遵守）",
        format_runtime_context_for_planner(policy),
        f"目标章节规模: 约 {policy.target_chapters or merged.get('chapter_range', ['?', '?'])[1]} 章",
    ]
    return "\n".join(lines)