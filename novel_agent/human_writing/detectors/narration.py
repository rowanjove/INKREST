"""Narration slop and over-explanation detector for HWE."""

from __future__ import annotations

import re
from typing import List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class NarrationDetector:
    """Scans for narrative explanation, author intrusion, mind-reading, and fake profound endings."""

    @classmethod
    def scan(cls, text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []
        narration_rules = [r for r in rules if r.family in ("narration", "staging") and r.detector_type == "narration" and r.enabled]

        for rule in narration_rules:
            for pattern_str in rule.patterns:
                try:
                    compiled = re.compile(pattern_str)
                except re.error:
                    continue

                for match in compiled.finditer(text):
                    m_start = match.start()
                    m_end = match.end()
                    matched_text = match.group(0)

                    # For chapter endings (e.g. FAKE_PROFOUND_ENDING), check if it's near the end of text
                    if "ending" in rule.id.lower() or "chapter" in rule.scope:
                        # Must occur within the last 25% of the text or last 2 paragraphs
                        if m_end < len(text) * 0.65:
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
