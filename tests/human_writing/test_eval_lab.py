"""Tests for HWE Eval Lab Runner and Fixtures."""

import pytest
from novel_agent.human_writing.eval import (
    EvalCase,
    HWEEvalRunner,
)


def test_eval_runner_load_cases():
    runner = HWEEvalRunner()
    cases = runner.load_cases()
    assert len(cases) >= 7

    pos_cases = [c for c in cases if c.expected_rules]
    neg_cases = [c for c in cases if not c.expected_rules]
    assert len(pos_cases) >= 5
    assert len(neg_cases) >= 2


def test_eval_runner_execution_and_fpr():
    runner = HWEEvalRunner()
    report = runner.run_eval()

    assert report.benchmark_name == "HWE 1.0 Benchmark Suite"
    assert report.metrics.total_cases >= 7
    assert report.metrics.negative_cases >= 2
    assert report.metrics.false_positives == 0
    assert report.metrics.false_positive_rate < 0.05
    assert report.fpr_target_met is True
    assert report.metrics.recall == 1.0
    assert report.metrics.precision == 1.0
    assert report.metrics.f1_score == 1.0


def test_eval_runner_custom_cases():
    custom_cases = [
        EvalCase(
            id="test_custom_pos",
            category="imagery",
            text="他面带微笑，眼中闪过一丝不易察觉的寒芒。",
            expected_rules=["HWE.IMAGERY.MICRO_EXPRESSION_CLICHE"],
        ),
        EvalCase(
            id="test_custom_neg",
            category="dialogue",
            text="“今天的风很大，”她拉紧了衣领，“我们回去吧。”",
            expected_rules=[],
        ),
    ]
    runner = HWEEvalRunner()
    report = runner.run_eval(custom_cases)

    assert report.metrics.total_cases == 2
    assert report.metrics.positive_cases == 1
    assert report.metrics.negative_cases == 1
    assert report.metrics.false_positives == 0
    assert report.metrics.false_positive_rate == 0.0
    assert report.fpr_target_met is True
