from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


SCALE_PROFILES: Dict[str, Dict[str, Any]] = {
    "micro": {
        "scale": "micro",
        "label": "微型短篇 (1-3章)",
        "chapter_range": [1, 3],
        "max_chapters": 3,
        "planning_mode": "single_shot",
        "outline_layers": [],
        "state_layers": [],
        "vector_enabled": False,
        "calibration_interval": 0,
    },
    "short": {
        "scale": "short",
        "label": "短篇小说 (4-20章)",
        "chapter_range": [4, 20],
        "max_chapters": 20,
        "planning_mode": "full_upfront",
        "outline_layers": ["L0", "L3"],
        "state_layers": ["high_freq"],
        "vector_enabled": False,
        "calibration_interval": 0,
    },
    "medium": {
        "scale": "medium",
        "label": "中篇小说 (20-100章)",
        "chapter_range": [21, 100],
        "max_chapters": 100,
        "planning_mode": "rolling_window",
        "outline_layers": ["L0", "L1", "L2", "L3"],
        "state_layers": ["high_freq", "mid_freq", "low_freq"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
    },
    "long": {
        "scale": "long",
        "label": "长篇小说 (100-500章)",
        "chapter_range": [101, 500],
        "max_chapters": 500,
        "planning_mode": "dynamic_volume",
        "outline_layers": ["L0", "L1_lite", "L2_dynamic", "L3"],
        "state_layers": ["hot", "warm"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "episode_volume": [50, 100],
        "hnsw_rebuild_every": 50,
        "embedding_backend": "chromadb",
    },
    "epic": {
        "scale": "epic",
        "label": "超长篇巨著 (500-3000章)",
        "chapter_range": [501, 3000],
        "max_chapters": 3000,
        "planning_mode": "fractal_dynamic_volume",
        "outline_layers": ["L0", "L1_minimal", "L2_dynamic", "L3"],
        "state_layers": ["hot", "warm", "cold", "archive"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "compress_hot_every": 10,
        "compress_warm_every": 50,
        "hnsw_rebuild_every": 50,
        "embedding_backend": "chromadb",
    },
    "infinite": {
        "scale": "infinite",
        "label": "无限更新连载",
        "chapter_range": [1, 999999],
        "max_chapters": 999999,
        "planning_mode": "container_episode",
        "outline_layers": ["container", "mainline", "episode", "L3"],
        "state_layers": ["persistent", "episode_temp"],
        "vector_enabled": True,
        "planning_window": 20,
        "calibration_interval": 20,
        "episode_chapters": [20, 50],
        "hnsw_rebuild_every": 50,
        "embedding_backend": "chromadb",
    },
}

LABEL_TO_SCALE = {
    "一章以内": "micro", "微型短篇 (1-3章)": "micro", "微型短篇": "micro",
    "几章": "short", "短篇小说 (4-20章)": "short", "短篇小说": "short",
    "几十章": "medium", "中篇小说 (20-100章)": "medium", "中篇小说": "medium",
    "一两百章": "long", "长篇小说 (100-500章)": "long", "长篇小说": "long",
    "几百上千章": "epic", "超长篇巨著 (500-3000章)": "epic", "超长篇巨著": "epic",
    "一直更新下去": "infinite", "无限更新连载": "infinite",
}
NEXT_SCALE = {
    "micro": "short",
    "short": "medium",
    "medium": "long",
    "long": "epic",
    "epic": "infinite",
}


def _outline_json_paths(root_dir: Path) -> list[Path]:
    root = Path(root_dir)
    return [root / "workspace" / "outline.json", root / "outline.json"]


def load_outline_scale_profile(root_dir: Path) -> Optional[Dict[str, Any]]:
    """Return scale_profile from workspace/outline.json (or legacy root outline.json)."""
    for outline_path in _outline_json_paths(root_dir):
        if not outline_path.exists():
            continue
        try:
            data = json.loads(outline_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        profile = data.get("scale_profile")
        if isinstance(profile, dict):
            return profile
    return None


def is_vector_enabled_for_project(root_dir: Path) -> bool:
    """Whether semantic vector recall/indexing should run for this project."""
    profile = load_outline_scale_profile(root_dir)
    if profile is None:
        # Legacy projects without scale_profile keep vector features on.
        return True
    return bool(profile.get("vector_enabled", True))


def resolve_scale_profile(
    target_chapters: Optional[int] = None,
    scale: str = "",
    scale_label: str = "",
) -> Dict[str, Any]:
    resolved = scale or LABEL_TO_SCALE.get(scale_label, "")
    if not resolved:
        resolved = _scale_for_target(int(target_chapters or 20))
    profile = deepcopy(SCALE_PROFILES.get(resolved, SCALE_PROFILES["medium"]))
    if target_chapters:
        profile["target_chapters"] = int(target_chapters)
    return profile


def build_upgrade_pressure(profile: Dict[str, Any], current_chapter_count: int) -> Dict[str, Any]:
    max_chapters = int(profile.get("max_chapters") or 0)
    scale = profile.get("scale", "medium")
    if not max_chapters or max_chapters >= 999999:
        return {"should_prompt": False, "ratio": 0, "recommended_scale": ""}
    ratio = current_chapter_count / max_chapters
    recommended = NEXT_SCALE.get(scale, "")
    return {
        "should_prompt": ratio >= 0.8 and bool(recommended),
        "ratio": round(ratio, 3),
        "recommended_scale": recommended,
    }


def _scale_for_target(target: int) -> str:
    if target <= 3:
        return "micro"
    if target <= 20:
        return "short"
    if target <= 100:
        return "medium"
    if target <= 500:
        return "long"
    return "epic"
