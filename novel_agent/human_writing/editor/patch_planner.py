"""Patch planning: groups nearby issues and defines minimal repair windows."""

from __future__ import annotations

from typing import List, Optional

from novel_agent.human_writing.detectors.matcher import TextStructure
from novel_agent.human_writing.schemas import HWEReport, PatchPlanItem, ProtectedSpan


def create_patch_plan(
    report: HWEReport,
    text: str,
    protected_spans: Optional[List[ProtectedSpan]] = None,
) -> List[PatchPlanItem]:
    """Analyze report issues and construct grouped, localized patch targets."""
    if not report.issues or not text:
        return []

    structure = TextStructure(text)
    all_protected = protected_spans or []
    patches: List[PatchPlanItem] = []

    # Sort issues by position
    sorted_issues = sorted(report.issues, key=lambda i: i.hwe.start)

    # Group issues that occur in the same paragraph or within close distance
    groups = []
    curr_group = []

    for issue in sorted_issues:
        if not curr_group:
            curr_group.append(issue)
        else:
            prev = curr_group[-1]
            # Same paragraph or start distance < 30 chars
            if issue.hwe.paragraph == prev.hwe.paragraph or (issue.hwe.start - prev.hwe.end) < 30:
                curr_group.append(issue)
            else:
                groups.append(curr_group)
                curr_group = [issue]
    if curr_group:
        groups.append(curr_group)

    # Build a patch item for each group
    for idx, group in enumerate(groups, start=1):
        rule_ids = list(dict.fromkeys(i.hwe.rule_id for i in group))
        families = list(dict.fromkeys(i.hwe.family for i in group))
        primary_family = families[0] if families else "staging"

        # Determine radius: narration or multiple issues -> paragraph; single staging/language -> sentence
        min_start = min(i.hwe.start for i in group)
        max_end = max(i.hwe.end for i in group)

        if "narration" in families or len(group) >= 2 or primary_family == "rhythm":
            radius = "paragraph"
            # Expand to paragraph boundary
            p_idx = group[0].hwe.paragraph
            if 1 <= p_idx <= len(structure.paragraphs):
                p_start, p_end, p_text = structure.paragraphs[p_idx - 1]
                # Strip leading/trailing newlines from span
                start_offset = p_start
                end_offset = p_end
                target_text = p_text.rstrip("\r\n")
                end_offset = p_start + len(target_text)
            else:
                start_offset = min_start
                end_offset = max_end
                target_text = text[start_offset:end_offset]
        else:
            radius = "sentence"
            # Find the sentence span covering min_start and max_end
            matching_sents = [
                s for s in structure.sentences
                if not (s.end <= min_start or s.start >= max_end)
            ]
            if matching_sents:
                start_offset = matching_sents[0].start
                end_offset = matching_sents[-1].end
                target_text = text[start_offset:end_offset]
            else:
                start_offset = min_start
                end_offset = max_end
                target_text = text[start_offset:end_offset]

        # Consolidated instruction
        instructions = [i.fix for i in group if i.fix]
        unique_inst = list(dict.fromkeys(instructions))
        instruction_str = "；".join(unique_inst) if unique_inst else "消除模板化痕迹，以具体动作与细节呈现。"

        # Filter relevant protected spans that intersect this patch window
        window_spans = [
            ps for ps in all_protected
            if ps.start is not None and ps.end is not None
            and not (ps.end < start_offset or ps.start > end_offset)
        ]

        # Calculate risk
        has_high = any(i.severity == "high" for i in group)
        risk = "high" if has_high else ("medium" if len(group) > 1 else "low")

        patches.append(
            PatchPlanItem(
                patch_id=f"patch-{idx:03d}",
                rule_ids=rule_ids,
                family=primary_family,
                start=start_offset,
                end=end_offset,
                radius=radius,
                original_text=target_text,
                instruction=instruction_str,
                risk=risk,
                protected_spans=window_spans,
            )
        )

    return patches
