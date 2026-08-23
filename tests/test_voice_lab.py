from pathlib import Path

from novel_agent.quality.prose_identity import build_prose_identity_profile, save_prose_identity_profile
from novel_agent.quality.voice_lab import build_voice_lab, record_voice_feedback, set_voice_lab_frozen


def test_voice_lab_exposes_evidence_trend_and_freeze_state(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("雨停了。她推开门，没有回头。", encoding="utf-8")
    profile = build_prose_identity_profile(
        [{"id": "sample", "kind": "user_sample", "path": "sample.txt", "text": sample.read_text(encoding="utf-8")}]
    )
    save_prose_identity_profile(tmp_path, profile)

    frozen = set_voice_lab_frozen(tmp_path, frozen=True, reason="人工确认声线")
    lab = build_voice_lab(tmp_path)
    assert lab["status"] == "calibrated"
    assert lab["frozen"] is True
    assert frozen["revision"] == 1
    assert lab["evidence"][0]["preview"] == "雨停了。她推开门，没有回头。"

    event = record_voice_feedback(tmp_path, {"kind": "false_positive", "chapter_id": "001", "note": "有意的节奏变化"})
    assert event["feedback_id"].startswith("voice-feedback:")
    assert build_voice_lab(tmp_path)["feedback_count"] == 1

    unfrozen = set_voice_lab_frozen(tmp_path, frozen=False)
    assert unfrozen["revision"] == 2
    assert build_voice_lab(tmp_path)["frozen"] is False
