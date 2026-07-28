"""Report-only scene-progress checks."""

import re
from typing import Any, Dict, List

# Patterns that indicate plot/action progression
ACTION_PATTERNS = [
    re.compile(r"走|跑|跳|飞|冲|离开|到达|进入|走出"),
    re.compile(r"说|喊|问|答|叫|骂|笑|哭"),
    re.compile(r"拿|放|扔|打|推|拉|踢|砍|刺"),
    re.compile(r"看|听|闻|感觉|发现|注意"),
    re.compile(r"开门|关门|坐下|站起|转身|回头"),
]

# Patterns that indicate static introspection
STATIC_PATTERNS = [
    re.compile(r"想|思考|回忆|沉思|琢磨|寻思"),
    re.compile(r"心中|内心|心里|脑海"),
    re.compile(r"感觉|觉得|认为|以为"),
]


def _count_pattern_matches(text: str, patterns: List[re.Pattern]) -> int:
    """Count total matches across all patterns."""
    count = 0
    for pattern in patterns:
        count += len(pattern.findall(text))
    return count


def check_scene_delta(text: str, short_chapter: bool = False) -> Dict[str, Any]:
    """Check if the chapter has sufficient plot/action progression.

    Returns a report with pass/fail, score, and details.
    """
    if not text:
        return {
            "pass": False,
            "level": "fail",
            "score": 0,
            "details": ["空文本"],
            "action_count": 0,
            "static_count": 0,
        }

    # Split into rough scenes by paragraph groups
    paragraphs = re.split(r"\n{2,}", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return {
            "pass": False,
            "level": "fail",
            "score": 0,
            "details": ["无段落"],
            "action_count": 0,
            "static_count": 0,
        }

    # Count action and static patterns
    action_count = _count_pattern_matches(text, ACTION_PATTERNS)
    static_count = _count_pattern_matches(text, STATIC_PATTERNS)

    # Calculate action density (per 1000 chars)
    text_len = len(text)
    action_density = action_count / max(1, text_len / 1000)
    static_density = static_count / max(1, text_len / 1000)

    # Check for scene-level progression
    # A "valid" scene has more action than static
    valid_scenes = 0
    low_delta_scenes = 0

    for para in paragraphs:
        para_action = _count_pattern_matches(para, ACTION_PATTERNS)
        para_static = _count_pattern_matches(para, STATIC_PATTERNS)
        if para_action > para_static:
            valid_scenes += 1
        if para_action < 2 and para_static > 3:
            low_delta_scenes += 1

    # Determine pass/fail
    min_valid = 1 if short_chapter else 2
    pass_condition = valid_scenes >= min_valid and low_delta_scenes <= 2

    # Calculate score
    action_ratio = action_count / max(1, action_count + static_count)
    scene_ratio = valid_scenes / max(1, len(paragraphs))
    score = int((action_ratio * 50 + scene_ratio * 50))
    if not pass_condition:
        score = min(score, 69)

    if score >= 70:
        level = "none"
    elif score >= 50:
        level = "warning"
    elif score >= 30:
        level = "review"
    else:
        level = "fail"

    details = []
    if valid_scenes < min_valid:
        details.append(f"有效场景不足：{valid_scenes}/{min_valid}")
    if low_delta_scenes > 2:
        details.append(f"静态段落过多：{low_delta_scenes}")

    return {
        "pass": pass_condition,
        "level": level,
        "score": score,
        "details": details,
        "action_count": action_count,
        "static_count": static_count,
        "valid_scenes": valid_scenes,
        "total_scenes": len(paragraphs),
        "low_delta_scenes": low_delta_scenes,
    }
