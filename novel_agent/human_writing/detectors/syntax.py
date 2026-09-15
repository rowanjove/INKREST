"""Regex and syntax pattern detector for HWE."""

from __future__ import annotations

import re
from typing import List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class SyntaxDetector:
    """Scans text for compiled regex syntax patterns."""

    @staticmethod
    def scan(text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []

        for rule in rules:
            if rule.detector_type != "regex" or not rule.enabled:
                continue

            for pattern_str in rule.patterns:
                try:
                    compiled = re.compile(pattern_str)
                except re.error:
                    continue

                for match in compiled.finditer(text):
                    m_start = match.start()
                    m_end = match.end()
                    matched_text = match.group(0)

                    # Negative checks for false positive avoidance on binary contrast:
                    # e.g., "不是三号，而是十三号" is factual correction, not slop contrast.
                    if rule.id == "HWE.STAGING.BINARY_CONTRAST":
                        # If the contrast is extremely short and pure numbers/facts, skip
                        neg = match.groupdict().get("neg", "")
                        pos = match.groupdict().get("pos", "")
                        if len(neg) <= 3 and len(pos) <= 3:
                            continue

                    issue = build_issue_from_match(
                        rule,
                        m_start,
                        m_end,
                        matched_text,
                        structure,
                    )
                    if issue:
                        issues.append(issue)

        return issues
