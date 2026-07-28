"""Paragraph fuzzy matching for audit-driven rewrites."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from novel_agent.logging_config import get_logger

logger = get_logger("audit_phase.matching")


def find_best_paragraph_match(
    paragraphs: List[str],
    target_text: str,
    threshold: float = 0.75,
) -> Tuple[Optional[str], int]:
    target_clean = target_text.strip("“\"”' \t\n")
    if not target_clean:
        return None, -1

    for idx, p in enumerate(paragraphs):
        if target_text in p or target_clean in p:
            return p, idx

    best_idx = -1
    best_ratio = 0.0
    target_chars = set(re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]", target_clean))
    if not target_chars:
        target_chars = set(target_clean)

    for idx, p in enumerate(paragraphs):
        p_clean = p.strip()
        n_p = len(p_clean)
        n_t = len(target_clean)

        p_chars = set(re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]", p_clean))
        if not p_chars:
            p_chars = set(p_clean)
        if target_chars and len(target_chars.intersection(p_chars)) / len(target_chars) < 0.20:
            continue

        if n_p >= n_t:
            sentences = [s.strip() for s in re.split(r"[。！？\n]", p_clean) if s.strip()]
            for s in sentences:
                ratio = SequenceMatcher(None, target_clean, s).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = idx
            for i in range(0, n_p - n_t + 1, max(1, n_t // 2)):
                window = p_clean[i : i + n_t]
                ratio = SequenceMatcher(None, target_clean, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = idx
        else:
            ratio = SequenceMatcher(None, target_clean, p_clean).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx

    if best_ratio >= threshold:
        logger.info(
            "Fuzzy matched paragraph index %d (similarity ratio: %.2f) for target: '%s'",
            best_idx,
            best_ratio,
            target_clean[:30],
        )
        return paragraphs[best_idx], best_idx

    return None, -1