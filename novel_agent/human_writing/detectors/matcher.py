"""Text segmentation and location matching utilities for HWE."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from novel_agent.human_writing.schemas import HWEIssue, HWEIssueDetail, HWERule


@dataclass
class SentenceSpan:
    text: str
    start: int
    end: int
    paragraph_idx: int
    line_idx: int
    is_dialogue: bool


class TextStructure:
    """Indexed structure of text supporting fast offset-to-location lookups."""

    def __init__(self, text: str):
        self.raw_text = text
        self.paragraphs: List[Tuple[int, int, str]] = []  # (start, end, text)
        self.sentences: List[SentenceSpan] = []
        self._index_structure()

    def _index_structure(self) -> None:
        lines = self.raw_text.splitlines(keepends=True)
        curr_offset = 0
        p_idx = 1
        line_idx = 1

        dialogue_pattern = re.compile(r"^[“”\"'「『].*?[”\"'」』]$")

        for line in lines:
            stripped = line.strip()
            line_len = len(line)
            if stripped:
                p_start = curr_offset
                p_end = curr_offset + line_len
                self.paragraphs.append((p_start, p_end, line))

                # Split into sentences while keeping exact offsets
                # Sentence boundary delimiters: 。！？!?；;\n
                sent_pattern = re.compile(r"[^。！？!?；;\n]+(?:[。！？!?；;]+[\"”'」』]?)?")
                for match in sent_pattern.finditer(line):
                    s_text = match.group(0)
                    if not s_text.strip():
                        continue
                    s_start = p_start + match.start()
                    s_end = p_start + match.end()
                    is_dial = bool(
                        dialogue_pattern.match(s_text.strip())
                        or "“" in s_text
                        or "”" in s_text
                        or "\"" in s_text
                    )
                    self.sentences.append(
                        SentenceSpan(
                            text=s_text,
                            start=s_start,
                            end=s_end,
                            paragraph_idx=p_idx,
                            line_idx=line_idx,
                            is_dialogue=is_dial,
                        )
                    )
                p_idx += 1
            curr_offset += line_len
            line_idx += 1

    def locate_offset(self, start: int, end: int) -> Tuple[int, int, bool, str, str]:
        """Return (paragraph_idx, line_idx, is_dialogue, context_before, context_after)."""
        paragraph_idx = 1
        line_idx = 1
        is_dialogue = False

        # Find line number
        line_idx = self.raw_text[:start].count("\n") + 1

        # Find paragraph
        for idx, (p_start, p_end, _) in enumerate(self.paragraphs, start=1):
            if p_start <= start < p_end or (idx == len(self.paragraphs) and start >= p_start):
                paragraph_idx = idx
                break

        # Check dialogue status
        for sent in self.sentences:
            if sent.start <= start < sent.end or sent.start < end <= sent.end:
                if sent.is_dialogue:
                    is_dialogue = True
                    break

        # Context windows
        ctx_start = max(0, start - 35)
        ctx_end = min(len(self.raw_text), end + 35)
        context_before = self.raw_text[ctx_start:start]
        context_after = self.raw_text[end:ctx_end]

        return paragraph_idx, line_idx, is_dialogue, context_before, context_after


def build_issue_from_match(
    rule: HWERule,
    start: int,
    end: int,
    matched_text: str,
    structure: TextStructure,
    custom_why: Optional[str] = None,
    custom_fix: Optional[str] = None,
) -> Optional[HWEIssue]:
    """Construct an HWEIssue, honoring rule fiction policies."""
    p_idx, l_idx, is_dial, ctx_before, ctx_after = structure.locate_offset(start, end)

    # Check dialogue suppression policy
    allow_dialogue = rule.fiction_policy.get("allow_if_dialogue", False)
    if is_dial and allow_dialogue:
        return None

    detail = HWEIssueDetail(
        rule_id=rule.id,
        family=rule.family,
        confidence=rule.confidence,
        start=start,
        end=end,
        line=l_idx,
        paragraph=p_idx,
        matched_text=matched_text,
        context_before=ctx_before,
        context_after=ctx_after,
        autofix="model_patch",
        blocking=rule.fiction_policy.get("auto_block", False),
        source="local_rule",
        explainable=True,
    )

    issue_type = rule.id.lower().replace(".", "_")
    audit_class = "CRITICAL" if rule.severity == "high" and detail.blocking else ("WARNING" if rule.severity in ("high", "medium") else "INFO")

    return HWEIssue(
        type=issue_type,
        issue_layer="text",
        severity=rule.severity,
        audit_class=audit_class,
        text=f"{rule.title}：{matched_text[:40]}",
        why=custom_why or rule.why,
        fix=custom_fix or rule.suggestion,
        hwe=detail,
    )
