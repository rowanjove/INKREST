from pathlib import Path

from novel_agent.quality.calibration import (
    build_mutation_cases,
    load_calibration_report,
    record_calibration_feedback,
    run_quality_calibration,
    save_golden_chapters,
)


def _chapter():
    return {
        "chapter_id": "001",
        "text": "雨停在旧城区的屋檐上。林澈握紧铜钥匙，沿着石阶向下走去。远处的灯一盏盏亮起，他没有回头。",
        "source": "test_fixture",
    }


def test_golden_chapters_are_explicit_and_mutations_are_deterministic(tmp_path: Path):
    save_golden_chapters(tmp_path, [_chapter()])
    result = run_quality_calibration(tmp_path, minimum_samples=1)

    assert result["status"] == "calibrated"
    assert result["sample_count"] == 1
    assert result["mutation_count"] >= 4
    assert result["mutation_match_rate"] == 1.0
    assert build_mutation_cases(_chapter()) == build_mutation_cases(_chapter())


def test_insufficient_samples_report_uncalibrated_and_feedback_is_local(tmp_path: Path):
    result = run_quality_calibration(tmp_path, chapters=[_chapter()], minimum_samples=20)

    assert result["status"] == "uncalibrated"
    assert load_calibration_report(tmp_path)["status"] == "uncalibrated"
    event = record_calibration_feedback(
        tmp_path,
        {"kind": "false_positive", "case_id": "001:style", "note": "叙事语气是有意的"},
    )
    assert event["feedback_id"].startswith("feedback:")
    assert load_calibration_report(tmp_path)["status"] == "uncalibrated"
