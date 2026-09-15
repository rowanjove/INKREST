"""Dialogue quality and mechanical exchange detector for HWE."""

from __future__ import annotations

import re
from typing import List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class DialogueDetector:
    """Scans for dialogue exposition, voice collapse, and ping-pong Q&A scripts."""

    @classmethod
    def scan(cls, text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []
        dialogue_rules = {r.id: r for r in rules if r.family == "dialogue" and r.enabled}

        # 1. Exposition & voice collapse regex/patterns inside dialogue
        for r_id in ("HWE.DIALOGUE.EXPOSITION_DIALOGUE", "HWE.DIALOGUE.VOICE_COLLAPSE"):
            rule = dialogue_rules.get(r_id)
            if not rule:
                continue

            for pattern_str in rule.patterns:
                try:
                    compiled = re.compile(pattern_str)
                except re.error:
                    continue

                for match in compiled.finditer(text):
                    m_start = match.start()
                    m_end = match.end()
                    # Dialogue rule only applies if match is actually inside dialogue
                    _, _, is_dial, _, _ = structure.locate_offset(m_start, m_end)
                    if not is_dial:
                        continue

                    # Temporarily allow dialogue check bypass so build_issue_from_match won't discard it
                    orig_policy = dict(rule.fiction_policy)
                    rule.fiction_policy["allow_if_dialogue"] = False
                    issue = build_issue_from_match(
                        rule,
                        m_start,
                        m_end,
                        match.group(0),
                        structure,
                    )
                    rule.fiction_policy = orig_policy
                    if issue:
                        issues.append(issue)

        # 2. Question-Answer ping pong chain (3+ rounds of consecutive alternating lines of dialogue)
        qa_rule = dialogue_rules.get("HWE.DIALOGUE.QUESTION_ANSWER_CHAIN")
        if qa_rule:
            dial_sents = [s for s in structure.sentences if s.is_dialogue]
            qa_streak = []
            is_question_next = True

            for sent in dial_sents:
                is_q = bool(re.search(r"[？\?]|(?:吗|呢|何在|为什么|何必|是谁)[”\"'」』]?$", sent.text.strip()))
                if is_question_next and is_q:
                    qa_streak.append(sent)
                    is_question_next = False
                elif not is_question_next and not is_q:
                    qa_streak.append(sent)
                    is_question_next = True
                else:
                    if len(qa_streak) >= 6:  # 3 full QA rounds = 6 utterances
                        first_s = qa_streak[0]
                        last_s = qa_streak[-1]
                        issue = build_issue_from_match(
                            qa_rule,
                            first_s.start,
                            last_s.end,
                            f"连续 {len(qa_streak)//2} 轮机械式一问一答对簿台词",
                            structure,
                        )
                        if issue:
                            issues.append(issue)
                    qa_streak = [sent] if is_q else []
                    is_question_next = not bool(qa_streak)

            if len(qa_streak) >= 6:
                first_s = qa_streak[0]
                last_s = qa_streak[-1]
                issue = build_issue_from_match(
                    qa_rule,
                    first_s.start,
                    last_s.end,
                    f"连续 {len(qa_streak)//2} 轮机械式一问一答对簿台词",
                    structure,
                )
                if issue:
                    issues.append(issue)

        return issues
