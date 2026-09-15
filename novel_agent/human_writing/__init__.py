"""Human Writing Engine (HWE) for INKREST.

Provides deterministic, explainable, and local-first prose quality scanning,
anti-slop rule enforcement, and protected-span aware patch planning.
"""

from novel_agent.human_writing.schemas import (
    HWERule,
    HWEIssue,
    HWEIssueDetail,
    HWEScores,
    HWEReport,
)
from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.human_writing.context_compiler import (
    HumanContextCompiler,
    HumanPromptContext,
    compile_human_writing_prompt,
)
from novel_agent.human_writing.memory import (
    ExpressionEntry,
    WindowDiagnostics,
    extract_expression_entries_v2,
    analyze_sliding_windows,
    detect_chapter_ending_fingerprint_repetition,
    analyze_dialogue_voice_drift,
)
from novel_agent.human_writing.semantic_reviewer import (
    HWESemanticReviewer,
    should_run_semantic_review,
)
from novel_agent.human_writing.preferences import HWEPreferenceManager

__all__ = [
    "HWERule",
    "HWEIssue",
    "HWEIssueDetail",
    "HWEScores",
    "HWEReport",
    "HumanWritingEngine",
    "HumanContextCompiler",
    "HumanPromptContext",
    "compile_human_writing_prompt",
    "ExpressionEntry",
    "WindowDiagnostics",
    "extract_expression_entries_v2",
    "analyze_sliding_windows",
    "detect_chapter_ending_fingerprint_repetition",
    "analyze_dialogue_voice_drift",
    "HWESemanticReviewer",
    "should_run_semantic_review",
    "HWEPreferenceManager",
]
