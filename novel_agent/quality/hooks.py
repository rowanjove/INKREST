"""Deterministic hook extraction from chapter tails and head continuity checking."""

import re
from typing import Any, Dict, List

ACTION_HOOKS = re.compile(r"(?:正要|准备|打算|决定|即将|就要|刚想|刚准备|开始|试图).{0,24}?(?:[，,；;。！？\n]|$)")
INJURY_HOOKS = re.compile(r"(受伤|流血|伤口|疼痛|昏迷|中毒|发热|发冷|虚弱|透支|内伤)")
PERCEPTION_HOOKS = re.compile(r"(?:发现|察觉|注意|看出|感觉到|意识到|听到|闻到|看到).{0,24}?(?:了|到|出|[，,；;。！？\n]|$)")


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _full_matches(pattern: re.Pattern, text: str) -> List[str]:
    return _unique([m.group(0).strip("，,；;。！？\n ") for m in pattern.finditer(text)])


def extract_tail_hooks(text: str, tail_chars: int = 500) -> Dict[str, Any]:
    """Extract hooks from the tail of a chapter text."""
    tail = (text or "")[-tail_chars:]
    return {
        "unfinished_actions": _full_matches(ACTION_HOOKS, tail),
        "injuries": _unique(INJURY_HOOKS.findall(tail)),
        "perceptions": _full_matches(PERCEPTION_HOOKS, tail),
        "keywords": _unique(re.findall(r"[一-鿿]{2,4}", tail))[:40],
    }


def check_head_continuity(
    prev_hooks: Dict[str, Any], current_text: str, head_chars: int = 700
) -> Dict[str, Any]:
    """Check if the head of current chapter continues hooks from previous chapter."""
    head = (current_text or "")[:head_chars]
    missing = []
    for hook_type in ("unfinished_actions", "injuries", "perceptions"):
        for hook in prev_hooks.get(hook_type, []) or []:
            if hook not in head:
                missing.append({"type": hook_type, "text": hook})
    total_hooks = sum(
        len(prev_hooks.get(k, []) or [])
        for k in ("unfinished_actions", "injuries", "perceptions")
    )
    score = max(0.0, 1.0 - len(missing) / max(1, total_hooks))
    return {
        "pass": len(missing) <= 1 and score >= 0.65,
        "score": round(score, 3),
        "missing_hooks": missing,
    }
