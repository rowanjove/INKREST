"""Data schemas for HWE Eval Lab."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single evaluation benchmark test case."""

    id: str
    category: str = "general"
    text: str
    expected_rules: List[str] = Field(default_factory=list)
    description: str = ""


class EvalResult(BaseModel):
    """Execution result for a single evaluation case."""

    case_id: str
    category: str
    expected_rules: List[str]
    detected_rules: List[str]
    is_false_positive: bool
    is_false_negative: bool
    is_true_positive: bool
    is_true_negative: bool
    duration_ms: float = 0.0
    error: Optional[str] = None


class EvalMetrics(BaseModel):
    """Aggregated benchmark performance metrics."""

    total_cases: int = 0
    positive_cases: int = 0
    negative_cases: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float = 1.0
    recall: float = 1.0
    f1_score: float = 1.0
    false_positive_rate: float = 0.0
    avg_latency_ms: float = 0.0


class EvalReport(BaseModel):
    """Comprehensive benchmark evaluation report."""

    benchmark_name: str = "HWE 1.0 Benchmark Suite"
    timestamp: str
    engine_version: str = "0.1.0"
    ruleset_version: str = "unknown"
    metrics: EvalMetrics = Field(default_factory=EvalMetrics)
    results: List[EvalResult] = Field(default_factory=list)
    fpr_target_met: bool = True
