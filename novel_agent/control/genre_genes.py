from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


DEFAULT_GENRE_GENES: Dict[str, Any] = {
    "pleasure_mechanism": "逆袭型",
    "protagonist_arc": "从弱到强",
    "romance_weight": "辅助线",
    "pacing_baseline": "快节奏爽文",
    "drift_guards": [
        "不要把电竞逆袭写成纯恋爱日常",
        "不要让主角核心目标脱离成长主线",
        "不要连续三章没有外部压力或可见进展",
    ],
}


def ensure_genre_genes(outline: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the outline has stable L0 genre genes.

    These fields are intended to be durable constraints for longform writing,
    not chapter-level details. Existing user or model values win over defaults.
    """
    result = deepcopy(outline)
    current = result.get("genre_genes")
    if not isinstance(current, dict):
        current = {}

    genes = deepcopy(DEFAULT_GENRE_GENES)
    genes.update({key: value for key, value in current.items() if value not in (None, "", [])})

    core_theme = str(result.get("core_theme") or result.get("genre_positioning") or "").strip()
    if core_theme and not any(core_theme in guard for guard in genes.get("drift_guards", [])):
        genes.setdefault("drift_guards", []).append(f"不要偏离核心主题：{core_theme}")

    result["genre_genes"] = genes
    return result

