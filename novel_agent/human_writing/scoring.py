"""Scoring and dimension evaluation model for HWE."""

from __future__ import annotations

from typing import Dict, List

from novel_agent.human_writing.schemas import HWEIssue, HWEScores


def calculate_hwe_scores(issues: List[HWEIssue], char_count: int) -> HWEScores:
    """Calculate multi-dimensional prose quality scores and template risk."""
    scores = HWEScores()
    if not issues:
        return scores

    # Severity weights
    sev_weights = {"low": 2.0, "medium": 5.0, "high": 10.0}

    # Deductions per dimension
    naturalness_penalties = 0.0
    rhythm_penalties = 0.0
    narrative_penalties = 0.0
    voice_penalties = 0.0
    freshness_penalties = 0.0

    # Total risk calculation
    total_penalty = 0.0

    for issue in issues:
        sev = issue.severity
        weight = sev_weights.get(sev, 4.0) * issue.hwe.confidence
        total_penalty += weight

        family = issue.hwe.family
        if family in ("staging", "language"):
            naturalness_penalties += weight
        elif family == "rhythm":
            rhythm_penalties += weight * 1.2
        elif family == "narration":
            narrative_penalties += weight * 1.3
        elif family == "dialogue":
            voice_penalties += weight * 1.2
        elif family in ("imagery", "longform"):
            freshness_penalties += weight

    # Scale penalties relative to text length (longer chapters naturally have more occurrences)
    char_scale = max(char_count / 1500.0, 1.0)

    scaled_nat = naturalness_penalties / char_scale
    scaled_rhy = rhythm_penalties / char_scale
    scaled_nar = narrative_penalties / char_scale
    scaled_voi = voice_penalties / char_scale
    scaled_fre = freshness_penalties / char_scale
    scaled_total = total_penalty / char_scale

    scores.naturalness = max(0, min(100, int(100 - scaled_nat * 2.2)))
    scores.rhythm = max(0, min(100, int(100 - scaled_rhy * 2.5)))
    scores.narrative_trust = max(0, min(100, int(100 - scaled_nar * 2.8)))
    scores.voice = max(0, min(100, int(100 - scaled_voi * 2.4)))
    scores.freshness = max(0, min(100, int(100 - scaled_fre * 2.2)))

    # Template risk is an aggregate risk index between 0 and 100
    scores.template_risk = min(100, int(scaled_total * 2.5))
    scores.overall_score = max(0, 100 - scores.template_risk)

    return scores
