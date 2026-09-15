"""Phrase and keyword detector for HWE."""

from __future__ import annotations

import re
from typing import List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class PhraseDetector:
    """Scans text for high-signal slop phrases and evaluates density thresholds."""

    @staticmethod
    def scan(text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []
        char_len = max(len(text), 1)
        per_1000_scale = char_len / 1000.0

        for rule in rules:
            if rule.detector_type != "phrase" or not rule.enabled:
                continue

            hits = []
            for pattern in rule.patterns:
                # Find all occurrences of the phrase
                start = 0
                while True:
                    idx = text.find(pattern, start)
                    if idx == -1:
                        break
                    hits.append((idx, idx + len(pattern), pattern))
                    start = idx + len(pattern)

            if not hits:
                continue

            thresholds = rule.thresholds or {}
            single_hit_policy = thresholds.get("single_hit", "report")
            per_1000_limit = thresholds.get("per_1000_chars")
            max_per_p = thresholds.get("max_per_paragraph")

            # Evaluate thresholds
            if single_hit_policy == "ignore" and len(hits) == 1:
                continue

            if per_1000_limit is not None:
                density = len(hits) / max(per_1000_scale, 0.5)
                if density < per_1000_limit and len(hits) <= 2:
                    continue

            # Check paragraph concentration if specified
            if max_per_p is not None:
                p_counts = {}
                for h_start, h_end, p_text in hits:
                    p_idx, _, _, _, _ = structure.locate_offset(h_start, h_end)
                    p_counts[p_idx] = p_counts.get(p_idx, 0) + 1

                for h_start, h_end, p_text in hits:
                    p_idx, _, _, _, _ = structure.locate_offset(h_start, h_end)
                    if p_counts.get(p_idx, 0) >= max_per_p:
                        issue = build_issue_from_match(
                            rule,
                            h_start,
                            h_end,
                            p_text,
                            structure,
                            custom_why=f"{rule.why}（本段内密集出现 {p_counts[p_idx]} 次）",
                        )
                        if issue:
                            issues.append(issue)
                continue

            # Standard hit reporting
            for h_start, h_end, p_text in hits:
                issue = build_issue_from_match(rule, h_start, h_end, p_text, structure)
                if issue:
                    issues.append(issue)

        return issues
