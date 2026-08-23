import json
from pathlib import Path

from novel_agent.quality.metrics import build_quality_metrics, metrics_csv, save_quality_baseline


def _write_report(root: Path, chapter_id: str, *, passed: bool, score: int):
    reports = root / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "quality.json").write_text(
        json.dumps(
            {
                "overall_pass": passed,
                "overall_score": score,
                "checks": {
                    "event_consistency": {
                        "findings": [{"type": "fact_conflict"}] if not passed else []
                    },
                    "expression_repetition": {"findings": [{"type": "repeated_template"}]},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_metrics_aggregate_reports_and_candidate_feedback(tmp_path: Path):
    _write_report(tmp_path, "001", passed=True, score=92)
    _write_report(tmp_path, "002", passed=False, score=61)
    feedback_path = tmp_path / "workspace" / "chapters" / "chapter_001" / "reports" / "candidate_feedback.jsonl"
    feedback_path.write_text(
        "\n".join(
            [
                json.dumps({"kind": "accept", "candidate_id": "a"}),
                json.dumps({"kind": "edit", "candidate_id": "a"}),
                json.dumps({"kind": "pairwise", "candidate_a": "a", "candidate_b": "b", "choice": "a"}),
            ]
        ),
        encoding="utf-8",
    )

    metrics = build_quality_metrics(tmp_path, minimum_samples=20)
    assert metrics["status"] == "uncalibrated"
    assert metrics["aggregate"]["quality_report_count"] == 2
    assert metrics["aggregate"]["quality_pass_rate"] == 0.5
    assert metrics["aggregate"]["fact_conflict_count"] == 1
    assert metrics["aggregate"]["candidate_accept_rate"] == 0.5
    assert metrics["aggregate"]["candidate_edit_ratio"] == 1.0
    assert "chapter_id" in metrics_csv(metrics).splitlines()[0]


def test_baseline_is_persisted_as_local_json(tmp_path: Path):
    payload = save_quality_baseline(tmp_path)
    path = tmp_path / "workspace" / "reports" / "quality_baseline.json"
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == payload["status"]
