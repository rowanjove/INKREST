"""Eval Lab Runner for Human Writing Engine."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import List, Optional

from novel_agent.human_writing.engine import HumanWritingEngine
from novel_agent.human_writing.eval.schemas import (
    EvalCase,
    EvalMetrics,
    EvalReport,
    EvalResult,
)

logger = logging.getLogger(__name__)

DEFAULT_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tests"
    / "fixtures"
    / "hwe"
)


class HWEEvalRunner:
    """Benchmark runner for testing and evaluating HWE accuracy and FPR."""

    def __init__(
        self,
        engine: Optional[HumanWritingEngine] = None,
        fixtures_dir: Optional[Path] = None,
    ):
        self.engine = engine or HumanWritingEngine()
        self.fixtures_dir = fixtures_dir or DEFAULT_FIXTURES_DIR

    def load_cases(self, fixtures_dir: Optional[Path] = None) -> List[EvalCase]:
        """Load benchmark cases from positive/ and negative/ fixtures."""
        target_dir = fixtures_dir or self.fixtures_dir
        cases: List[EvalCase] = []
        if not target_dir.exists() or not target_dir.is_dir():
            logger.warning("Fixtures directory not found: %s", target_dir)
            return cases

        for path in sorted(target_dir.glob("**/*.json")):
            try:
                content = path.read_text(encoding="utf-8")
                raw = json.loads(content)
                if isinstance(raw, list):
                    for item in raw:
                        cases.append(EvalCase.model_validate(item))
                elif isinstance(raw, dict):
                    cases.append(EvalCase.model_validate(raw))
            except Exception as ex:
                logger.error("Failed to load fixture %s: %s", path, ex)

        return cases

    def run_eval(
        self,
        cases: Optional[List[EvalCase]] = None,
        benchmark_name: str = "HWE 1.0 Benchmark Suite",
    ) -> EvalReport:
        """Execute benchmark suite and calculate precision, recall, and FPR."""
        test_cases = cases if cases is not None else self.load_cases()

        results: List[EvalResult] = []
        total_latency_ms = 0.0

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        pos_count = 0
        neg_count = 0

        for case in test_cases:
            start_t = time.perf_counter()
            err_msg: Optional[str] = None
            detected_rules: List[str] = []

            try:
                report = self.engine.scan_text(case.text)
                detected_rules = [issue.hwe.rule_id for issue in report.issues]
            except Exception as ex:
                err_msg = str(ex)
                logger.exception("Error scanning eval case %s", case.id)

            duration_ms = (time.perf_counter() - start_t) * 1000
            total_latency_ms += duration_ms

            is_negative = len(case.expected_rules) == 0
            if is_negative:
                neg_count += 1
                is_fp = len(detected_rules) > 0
                is_tn = len(detected_rules) == 0
                is_tp = False
                is_fn = False
                if is_fp:
                    fp += 1
                else:
                    tn += 1
            else:
                pos_count += 1
                expected_set = set(case.expected_rules)
                detected_set = set(detected_rules)
                is_tp = len(expected_set.intersection(detected_set)) > 0
                is_fn = not is_tp
                is_fp = False
                is_tn = False
                if is_tp:
                    tp += 1
                else:
                    fn += 1

            results.append(
                EvalResult(
                    case_id=case.id,
                    category=case.category,
                    expected_rules=case.expected_rules,
                    detected_rules=detected_rules,
                    is_false_positive=is_fp,
                    is_false_negative=is_fn,
                    is_true_positive=is_tp,
                    is_true_negative=is_tn,
                    duration_ms=round(duration_ms, 2),
                    error=err_msg,
                )
            )

        total_cases = len(test_cases)
        fpr = (fp / neg_count) if neg_count > 0 else 0.0
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        avg_latency = (total_latency_ms / total_cases) if total_cases > 0 else 0.0

        metrics = EvalMetrics(
            total_cases=total_cases,
            positive_cases=pos_count,
            negative_cases=neg_count,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=round(fpr, 4),
            avg_latency_ms=round(avg_latency, 2),
        )

        fpr_target_met = fpr < 0.05

        return EvalReport(
            benchmark_name=benchmark_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            engine_version="1.0.0",
            ruleset_version=self.engine.registry.ruleset_version,
            metrics=metrics,
            results=results,
            fpr_target_met=fpr_target_met,
        )
