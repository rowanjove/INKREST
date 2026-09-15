"""Core engine facade for Human Writing Engine (HWE)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from novel_agent.human_writing.detectors.dialogue import DialogueDetector
from novel_agent.human_writing.detectors.matcher import TextStructure
from novel_agent.human_writing.detectors.narration import NarrationDetector
from novel_agent.human_writing.detectors.phrase import PhraseDetector
from novel_agent.human_writing.detectors.repetition import RepetitionDetector
from novel_agent.human_writing.detectors.rhythm import RhythmDetector
from novel_agent.human_writing.detectors.syntax import SyntaxDetector
from novel_agent.human_writing.rules.registry import RuleRegistry, get_rule_registry
from novel_agent.human_writing.schemas import HWEIssue, HWEReport
from novel_agent.human_writing.scoring import calculate_hwe_scores

logger = logging.getLogger(__name__)


class HumanWritingEngine:
    """Deterministic local scanner for AI novel slop and prose quality issues."""

    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or get_rule_registry()

    def scan_text(
        self,
        text: str,
        chapter_id: Optional[str] = None,
        revision_id: Optional[str] = None,
        mode: str = "assist",
        preferences: Optional[Any] = None,
    ) -> HWEReport:
        """Perform full local deterministic scan on given prose text."""
        start_time = time.perf_counter()
        if not text or not text.strip():
            return HWEReport(
                chapter_id=chapter_id,
                document_revision_id=revision_id,
                ruleset_version=self.registry.ruleset_version,
                mode=mode,
                char_count=0,
                summary="文本为空，无需分析",
            )

        structure = TextStructure(text)
        rules = self.registry.list_rules(enabled_only=True)

        raw_issues: List[HWEIssue] = []

        # 1. Run all deterministic detectors
        raw_issues.extend(PhraseDetector.scan(text, structure, rules))
        raw_issues.extend(SyntaxDetector.scan(text, structure, rules))
        raw_issues.extend(RhythmDetector.scan(text, structure, rules))
        raw_issues.extend(NarrationDetector.scan(text, structure, rules))
        raw_issues.extend(DialogueDetector.scan(text, structure, rules))
        raw_issues.extend(RepetitionDetector.scan(text, structure, rules))

        # 2. De-duplicate overlapping matches with same rule_id or same exact span
        deduped_issues: List[HWEIssue] = []
        seen_spans = set()

        for issue in sorted(raw_issues, key=lambda i: (i.hwe.start, -i.hwe.confidence)):
            key = (issue.hwe.rule_id, issue.hwe.start, issue.hwe.end)
            if key in seen_spans:
                continue
            seen_spans.add(key)
            deduped_issues.append(issue)

        if preferences is not None and hasattr(preferences, "filter_issues"):
            deduped_issues = preferences.filter_issues(deduped_issues)

        # 3. Aggregate statistics
        by_family: Dict[str, int] = {}
        by_sev: Dict[str, int] = {}
        for issue in deduped_issues:
            fam = issue.hwe.family
            by_family[fam] = by_family.get(fam, 0) + 1
            sev = issue.severity
            by_sev[sev] = by_sev.get(sev, 0) + 1

        scores = calculate_hwe_scores(deduped_issues, len(text))

        # 4. Generate diagnosis summary
        duration_ms = (time.perf_counter() - start_time) * 1000
        summary_parts = []
        if not deduped_issues:
            summary_parts.append("文风自然，未检出明显套路与模板腔。")
        else:
            top_fam = max(by_family.items(), key=lambda item: item[1])[0]
            summary_parts.append(
                f"检出 {len(deduped_issues)} 处文风瑕疵（主要集中在 {top_fam} 类别）。"
            )
            if scores.template_risk > 40:
                summary_parts.append(f"模板风险偏高 ({scores.template_risk}/100)，建议重点修复解释腔与机械节奏。")
            else:
                summary_parts.append(f"整体文风健康 ({scores.overall_score}/100)。")

        report = HWEReport(
            chapter_id=chapter_id,
            document_revision_id=revision_id,
            engine_version="0.1.0",
            ruleset_version=self.registry.ruleset_version,
            mode=mode,
            char_count=len(text),
            scores=scores,
            issues=deduped_issues,
            issue_counts_by_family=by_family,
            issue_counts_by_severity=by_sev,
            summary=" ".join(summary_parts),
        )

        logger.info(
            "HWE scan completed in %.2f ms, %d chars, %d issues, risk: %d",
            duration_ms,
            len(text),
            len(deduped_issues),
            scores.template_risk,
        )
        return report
