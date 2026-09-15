"""Rhythm and structural monotony detector for HWE."""

from __future__ import annotations

import math
import re
from typing import Dict, List

from novel_agent.human_writing.detectors.matcher import TextStructure, build_issue_from_match
from novel_agent.human_writing.schemas import HWEIssue, HWERule


class RhythmDetector:
    """Detects mechanical rhythm, staccato abuse, parallelism, and paragraph repetition."""

    @classmethod
    def scan(cls, text: str, structure: TextStructure, rules: List[HWERule]) -> List[HWEIssue]:
        issues: List[HWEIssue] = []
        rule_map: Dict[str, HWERule] = {r.id: r for r in rules if r.family == "rhythm" and r.enabled}

        # 1. Pattern-based rhythm rules (triple lists, parallelism)
        for r_id in ("HWE.RHYTHM.TRIPLE_LIST_OVERUSE", "HWE.RHYTHM.PARALLELISM_OVERUSE"):
            rule = rule_map.get(r_id)
            if not rule:
                continue
            for pat_str in rule.patterns:
                try:
                    compiled = re.compile(pat_str)
                except re.error:
                    continue
                for match in compiled.finditer(text):
                    issue = build_issue_from_match(
                        rule,
                        match.start(),
                        match.end(),
                        match.group(0),
                        structure,
                    )
                    if issue:
                        issues.append(issue)

        # 2. Staccato abuse: consecutive short sentences (e.g. >= 5 sentences with <= 6 chars)
        staccato_rule = rule_map.get("HWE.RHYTHM.STACCATO_ABUSE")
        if staccato_rule:
            short_streak = []
            for sent in structure.sentences:
                cleaned = sent.text.strip().rstrip("。！？!?；;\"”'」』")
                if 1 <= len(cleaned) <= 6:
                    short_streak.append(sent)
                else:
                    if len(short_streak) >= 5:
                        first_s = short_streak[0]
                        last_s = short_streak[-1]
                        combined_text = "".join(s.text for s in short_streak)
                        issue = build_issue_from_match(
                            staccato_rule,
                            first_s.start,
                            last_s.end,
                            combined_text,
                            structure,
                            custom_why=f"连续出现 {len(short_streak)} 个超短单句，节奏破碎且缺乏张力",
                        )
                        if issue:
                            issues.append(issue)
                    short_streak = []
            if len(short_streak) >= 5:
                first_s = short_streak[0]
                last_s = short_streak[-1]
                combined_text = "".join(s.text for s in short_streak)
                issue = build_issue_from_match(
                    staccato_rule,
                    first_s.start,
                    last_s.end,
                    combined_text,
                    structure,
                    custom_why=f"连续出现 {len(short_streak)} 个超短单句，节奏破碎且缺乏张力",
                )
                if issue:
                    issues.append(issue)

        # 3. Repetitive paragraph opening: 3+ consecutive paragraphs starting with the same 2-4 chars
        opening_rule = rule_map.get("HWE.RHYTHM.REPETITIVE_OPENING")
        if opening_rule and len(structure.paragraphs) >= 3:
            streak = []
            last_prefix = ""
            for p_start, p_end, p_text in structure.paragraphs:
                prefix = p_text.strip()[:3]
                if len(prefix) >= 2 and prefix == last_prefix:
                    streak.append((p_start, p_end, p_text))
                else:
                    if len(streak) >= 3:
                        issue = build_issue_from_match(
                            opening_rule,
                            streak[0][0],
                            streak[-1][1],
                            f"连续 {len(streak)} 段以‘{last_prefix}’开头",
                            structure,
                        )
                        if issue:
                            issues.append(issue)
                    last_prefix = prefix
                    streak = [(p_start, p_end, p_text)]
            if len(streak) >= 3:
                issue = build_issue_from_match(
                    opening_rule,
                    streak[0][0],
                    streak[-1][1],
                    f"连续 {len(streak)} 段以‘{last_prefix}’开头",
                    structure,
                )
                if issue:
                    issues.append(issue)

        # 4. Uniform sentence length (low variance coefficient in a paragraph with >= 5 sentences)
        uniform_rule = rule_map.get("HWE.RHYTHM.UNIFORM_SENTENCE_LENGTH")
        if uniform_rule:
            # Group sentences by paragraph_idx
            p_sents: Dict[int, List] = {}
            for s in structure.sentences:
                p_sents.setdefault(s.paragraph_idx, []).append(s)

            for p_idx, sents in p_sents.items():
                if len(sents) < 5:
                    continue
                lengths = [len(s.text.strip()) for s in sents if len(s.text.strip()) > 0]
                if not lengths:
                    continue
                mean = sum(lengths) / len(lengths)
                if mean < 8:  # Skip tiny fragments
                    continue
                variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
                std_dev = math.sqrt(variance)
                cv = std_dev / mean
                if cv < 0.16:  # Very uniform length
                    first_s = sents[0]
                    last_s = sents[-1]
                    issue = build_issue_from_match(
                        uniform_rule,
                        first_s.start,
                        last_s.end,
                        f"段落内连续 {len(sents)} 句句长极度均一（均长约 {int(mean)} 字，方差系数 {cv:.2f}）",
                        structure,
                    )
                    if issue:
                        issues.append(issue)

        return issues
