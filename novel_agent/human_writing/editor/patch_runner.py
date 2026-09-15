"""Patch runner: executes localized Three-Pass repairs and validates candidates."""

from __future__ import annotations

import difflib
import re
from typing import Callable, Optional

from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.human_writing.fidelity import validate_fidelity
from novel_agent.human_writing.schemas import HWEPatchCandidate, PatchPlanItem


def _heuristic_three_pass_repair(text: str) -> str:
    """Deterministic local three-pass transformer for high-signal slop."""
    result = text

    # Pass 1: Delete filler transitions and meta commentary
    result = re.sub(r"(?:与此同时|殊不知|显而易见的是|毋庸置疑|值得一提的是)[，,]\s*", "", result)
    result = re.sub(r"(?:简而言之|总而言之|换句话说|总的来看)[，,]\s*", "", result)

    # Pass 2: Break binary contrasts & stock comparisons
    # 不是A，而是B -> 转化为直接陈述
    def _fix_contrast(m: re.Match) -> str:
        pos = m.group(1).strip()
        return pos
    result = re.sub(r"(?:不是|并非|不只是|不仅是)[^，。！？]{2,25}[，,](?:而是|更是)([^，。！？]{2,25})", _fix_contrast, result)

    # Delete redundant explanation after physical action (Over-explanation)
    # e.g. "紧攥着拳头。显然他很害怕，内心的愤怒也在疯狂滋长。" -> "紧攥着拳头。"
    result = re.sub(
        r"((?:紧攥着拳头|咬紧牙关|低下头|别过脸|后退了一步|瘫坐在地|脸色发白)[。，；！])"
        r"[^。！？\n]{0,10}(?:显然|可以看出|分明|事实上|他是在|这意味着|他知道自己|他意识到自己)[^。！？\n]{0,25}(?:害怕|愤怒|紧张|绝望|不安|痛恨|恐惧)[。！？]?",
        r"\1",
        result,
    )

    # Stock metaphors cleanup
    result = result.replace("空气仿佛凝固了一般", "四周一片死寂")
    result = result.replace("空气仿佛凝固", "屋里一片寂静")
    result = result.replace("犹如热锅上的蚂蚁", "焦躁不安")
    result = result.replace("时间在这一刻凝固", "万籁俱寂")

    # Clean double punctuation or whitespace
    result = re.sub(r"[，,]{2,}", "，", result)
    result = re.sub(r"[。]{2,}", "。", result)
    return result.strip()


def run_patch(
    patch: PatchPlanItem,
    engine: Optional[HumanWritingEngine] = None,
    generator: Optional[Callable[[PatchPlanItem], str]] = None,
    max_edit_ratio: float = 0.55,
) -> HWEPatchCandidate:
    """Generate and validate a localized patch candidate for a PatchPlanItem."""
    active_engine = engine or HumanWritingEngine()

    # 1. Generate candidate text
    if generator is not None:
        raw_candidate = generator(patch)
    else:
        raw_candidate = _heuristic_three_pass_repair(patch.original_text)

    # If heuristic didn't change anything, ensure candidate is at least valid
    candidate_text = raw_candidate if raw_candidate else patch.original_text

    # 2. Validate fidelity
    fidelity = validate_fidelity(
        original_text=patch.original_text,
        candidate_text=candidate_text,
        protected_spans=patch.protected_spans,
        max_edit_ratio=max_edit_ratio,
    )

    # 3. Rescan candidate to calculate quality gain
    old_scan = active_engine.scan_text(patch.original_text)
    new_scan = active_engine.scan_text(candidate_text)

    old_issue_count = len(old_scan.issues)
    new_issue_count = len(new_scan.issues)
    quality_gain = max(0, (old_issue_count - new_issue_count) * 15 + (old_scan.scores.template_risk - new_scan.scores.template_risk))

    # 4. Utility scoring (PRD Section 32)
    fidelity_penalty = 50.0 if not fidelity.passed else 0.0
    edit_penalty = fidelity.edit_ratio * 15.0
    utility = float(quality_gain) - fidelity_penalty - edit_penalty

    # 5. Generate unified diff
    orig_lines = patch.original_text.splitlines(keepends=True)
    cand_lines = candidate_text.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            cand_lines,
            fromfile=f"original/{patch.patch_id}",
            tofile=f"patched/{patch.patch_id}",
        )
    )
    diff_str = "".join(diff_lines)

    return HWEPatchCandidate(
        patch_id=patch.patch_id,
        rule_ids=patch.rule_ids,
        start=patch.start,
        end=patch.end,
        original_text=patch.original_text,
        candidate_text=candidate_text,
        instruction=patch.instruction,
        fidelity=fidelity,
        utility=round(utility, 2),
        quality_gain=quality_gain,
        diff_unified=diff_str,
        status="pending",
    )
