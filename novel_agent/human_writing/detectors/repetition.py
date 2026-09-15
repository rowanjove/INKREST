"""Repetition and longform pattern saturation detector for HWE."""

from __future__ import annotations

import re
from typing import List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class RepetitionDetector:
    """Scans for repeated body reactions, stock metaphors, and chapter ending cliches."""

    @classmethod
    def scan(cls, text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []
        repetition_rules = [r for r in rules if r.detector_type == "repetition" and r.enabled]

        for rule in repetition_rules:
            for pat_str in rule.patterns:
                try:
                    compiled = re.compile(pat_str)
                except re.error:
                    continue

                for match in compiled.finditer(text):
                    m_start = match.start()
                    m_end = match.end()
                    # For chapter ending repeat, check if it's near the end
                    if "ending" in rule.id.lower():
                        if m_end < len(text) * 0.70:
                            continue

                    issue = build_issue_from_match(
                        rule,
                        m_start,
                        m_end,
                        match.group(0),
                        structure,
                    )
                    if issue:
                        issues.append(issue)

        return issues
