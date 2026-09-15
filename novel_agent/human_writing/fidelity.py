"""Fidelity validator for ensuring facts, names, and numbers are preserved."""

from __future__ import annotations

import difflib
import re
from typing import List

from novel_agent.human_writing.schemas import FidelityResult, ProtectedSpan

_CODE_FENCE_RE = re.compile(r"```|~~~")
_META_WRAPPER_RE = re.compile(
    r"(?i)(?:以下是|下面是|这是|现将)?\s*(?:修订|修改|润色|重写)(?:后的)?(?:完整)?正文\s*[:：]?"
)
_META_EXPLANATION_RE = re.compile(
    r"(?i)(?:修改说明|修订说明|改写说明|说明|注：|备注：)\s*[:：]?"
)


def validate_fidelity(
    original_text: str,
    candidate_text: str,
    protected_spans: List[ProtectedSpan],
    max_edit_ratio: float = 0.55,
) -> FidelityResult:
    """Check that candidate text preserves all protected entities and respects boundaries."""
    violations: List[str] = []
    preserved: List[ProtectedSpan] = []
    missing: List[ProtectedSpan] = []

    norm_orig = str(original_text or "").strip()
    norm_cand = str(candidate_text or "").strip()

    if not norm_cand:
        return FidelityResult(
            passed=False,
            violations=["候选文本为空"],
            length_delta=-len(norm_orig),
            edit_ratio=1.0,
        )

    # 1. Check for AI meta-talk and markdown fence artifacts
    if _CODE_FENCE_RE.search(norm_cand):
        violations.append("候选包含代码块标记 (```)")
    if _META_WRAPPER_RE.search(norm_cand) or _META_EXPLANATION_RE.search(norm_cand):
        violations.append("候选包含模型元说明或套话前缀")

    # 2. Verify all protected spans in original text are preserved
    for span in protected_spans:
        val = span.value.strip()
        if not val or val not in norm_orig:
            continue

        if span.policy in ("exact", "must_preserve"):
            if val in norm_cand:
                preserved.append(span)
            else:
                missing.append(span)
                violations.append(f"关键信息丢失 ({span.kind}): ‘{val}’")
        elif span.policy == "semantic_exact":
            # Strip whitespace and compare
            clean_val = re.sub(r"\s+", "", val)
            clean_cand = re.sub(r"\s+", "", norm_cand)
            if clean_val in clean_cand:
                preserved.append(span)
            else:
                missing.append(span)
                violations.append(f"时间/事实语义改变 ({span.kind}): ‘{val}’")

    # 3. Edit distance calculation
    matcher = difflib.SequenceMatcher(None, norm_orig, norm_cand)
    similarity = matcher.ratio()
    edit_ratio = max(0.0, 1.0 - similarity)

    if edit_ratio > max_edit_ratio:
        violations.append(
            f"改动幅度过大 (差异率 {edit_ratio:.1%} > 上限 {max_edit_ratio:.1%})"
        )

    length_delta = len(norm_cand) - len(norm_orig)
    passed = len(violations) == 0

    return FidelityResult(
        passed=passed,
        violations=violations,
        preserved_spans=preserved,
        missing_spans=missing,
        edit_ratio=round(edit_ratio, 3),
        length_delta=length_delta,
    )
