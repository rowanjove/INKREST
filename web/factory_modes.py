"""Single source of truth for AI factory modes (labels synced to frontend JSON)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

_EMBEDDED_MANIFEST: Dict[str, Any] = {
    "default": "newbie_auto",
    "modes": [
        "newbie_auto",
        "author_copilot",
        "platform_review",
        "longform_stable",
        "studio",
    ],
    "labels": {
        "newbie_auto": "新手全自动",
        "author_copilot": "作者协作",
        "platform_review": "平台过审",
        "longform_stable": "长篇稳定",
        "studio": "工作室生产",
    },
    "profiles": {
        "newbie_auto": {
            "label": "新手全自动",
            "automation_level": "high",
            "priorities": ["跳过复杂配置", "自动补齐开书要素", "阻断后优先自修"],
            "operator_hint": "适合从一个灵感直接推进，系统会优先给默认答案和下一步动作。",
        },
        "author_copilot": {
            "label": "作者协作",
            "automation_level": "balanced",
            "priorities": ["人工随时介入", "保留改稿入口", "展示更多产物与报告"],
            "operator_hint": "适合有写作经验的作者，把 AI 当副手而不是全自动代写机。",
        },
        "platform_review": {
            "label": "平台过审",
            "automation_level": "high",
            "priorities": ["AI 味风险", "敏感风险", "导出前风险总检"],
            "operator_hint": "适合准备投放或投稿，系统会更突出过审风险和自动改写入口。",
        },
        "longform_stable": {
            "label": "长篇稳定",
            "automation_level": "balanced",
            "priorities": ["设定连续性", "人物线追踪", "伏笔回收"],
            "operator_hint": "适合百章以上项目，系统会优先提醒记忆、向量和状态同步风险。",
        },
        "studio": {
            "label": "工作室生产",
            "automation_level": "managed",
            "priorities": ["多书进度", "待处理章节", "批量导出"],
            "operator_hint": "适合多项目管理，系统会更突出生产队列、风险聚合和批量动作。",
        },
    },
}


def _manifest_candidates() -> Tuple[Path, ...]:
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / "factory_modes.json",
        module_dir / "frontend" / "src" / "constants" / "factoryModes.json",
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_dir / "web" / "factory_modes.json",
                exe_dir / "_internal" / "web" / "factory_modes.json",
            ]
        )
    return tuple(candidates)


def _load_manifest() -> Dict[str, Any]:
    for path in _manifest_candidates():
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return dict(_EMBEDDED_MANIFEST)


_MANIFEST = _load_manifest()
FACTORY_MODE_IDS: Tuple[str, ...] = tuple(_MANIFEST.get("modes") or _EMBEDDED_MANIFEST["modes"])
FACTORY_MODE_LABELS: Dict[str, str] = dict(
    _MANIFEST.get("labels") or _EMBEDDED_MANIFEST["labels"]
)
DEFAULT_FACTORY_MODE: str = str(_MANIFEST.get("default") or _EMBEDDED_MANIFEST["default"])

if DEFAULT_FACTORY_MODE not in FACTORY_MODE_IDS:
    raise ValueError(f"default factory mode {DEFAULT_FACTORY_MODE!r} missing from modes list")


def factory_mode_profiles() -> Dict[str, Dict[str, Any]]:
    profiles = _MANIFEST.get("profiles") or _EMBEDDED_MANIFEST["profiles"]
    result: Dict[str, Dict[str, Any]] = {}
    for mode in FACTORY_MODE_IDS:
        profile = profiles.get(mode)
        if isinstance(profile, dict):
            result[mode] = {"mode": mode, **profile}
    return result


def is_valid_factory_mode(mode: str) -> bool:
    return mode in FACTORY_MODE_IDS


def factory_mode_label(mode: str) -> str:
    return FACTORY_MODE_LABELS.get(mode, mode)