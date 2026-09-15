"""Context budget management for ShanShan Assistant.

Ensures prompt stays within token budget limits:
System / Skill: ~3K
Selection / Current Paragraph: ~2K
Active Chapter Context: ~8K
Characters & World: ~4K
History & Dialog: ~2K
"""

from __future__ import annotations

from typing import Dict, Any


def approximate_tokens(text: str) -> int:
    """Rough token count estimation: ~1.5 tokens per Chinese char, ~1 token per 4 English chars."""
    if not text:
        return 0
    # A fast, lightweight heuristic suitable for Chinese/English mixed text
    count = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            count += 2
        else:
            count += 1
    return max(1, count // 2)


def truncate_to_tokens(text: str, max_tokens: int, suffix: str = "…(截断)") -> str:
    """Truncates text safely preserving head and tail if applicable."""
    if approximate_tokens(text) <= max_tokens:
        return text
    # Character limit estimation
    char_limit = max_tokens * 2
    if len(text) <= char_limit:
        return text
    return text[:char_limit - len(suffix)] + suffix
