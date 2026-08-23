import json
from pathlib import Path

from novel_agent.quality.prose_identity import (
    build_prose_identity_profile,
    build_prose_identity_profile_from_paths,
    compare_prose_identity,
    load_prose_identity_profile,
    list_prose_identity_profile_versions,
    restore_prose_identity_profile,
    save_prose_identity_profile,
)
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.quality_rewrite import build_quality_rewrite_hints


def test_profile_keeps_source_digests_and_extracts_rhythm_without_source_text():
    profile = build_prose_identity_profile(
        [
            {"id": "sample-a", "kind": "user_sample", "text": "雨落在窗上。林澈没有回头。"},
            {"id": "chapter-001", "kind": "accepted_chapter", "text": "门缝里亮着一线灯。\n他把钥匙收回掌心。"},
        ]
    )
    assert profile["status"] == "calibrated"
    assert profile["sample_count"] == 2
    assert profile["sources"][0]["sha256"]
    assert "text" not in profile["sources"][0]
    assert profile["rhythm"]["sentence_length"]["count"] >= 4
    assert profile["profile_id"]


def test_uncalibrated_profile_is_report_only():
    profile = build_prose_identity_profile([])
    result = compare_prose_identity("一句正文。", profile)
    assert profile["status"] == "uncalibrated"
    assert result["enabled"] is False
    assert result["pass"] is True
    assert result["blocking"] is False


def test_compare_same_text_is_close_and_different_rhythm_is_review():
    source = "短句。再短句。这里是一句稍微长一些的句子，用来形成变化。\n新段落继续推进。"
    profile = build_prose_identity_profile([source])
    same = compare_prose_identity(source, profile)
    different = compare_prose_identity("这是一个非常非常长的段落，没有对白，也没有明显的句号", profile)
    assert same["score"] >= 95
    assert same["status"] == "ok"
    assert different["score"] < same["score"]
    assert different["pass"] is True
    assert different["blocking"] is False


def test_profile_can_be_built_from_paths_and_saved_explicitly(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("她推开门。风从走廊尽头吹来。", encoding="utf-8")
    profile = build_prose_identity_profile_from_paths([sample], root_dir=tmp_path)
    target = save_prose_identity_profile(tmp_path, profile)
    assert target == tmp_path / "assets" / "prose_identity_profile.json"
    loaded = load_prose_identity_profile(tmp_path)
    assert loaded is not None
    assert loaded["profile_id"] == profile["profile_id"]
    assert loaded["sources"][0]["path"] == "sample.txt"
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 1


def test_invalid_profile_is_ignored_on_load(tmp_path: Path):
    target = tmp_path / "assets" / "prose_identity_profile.json"
    target.parent.mkdir(parents=True)
    target.write_text("{\"schema_version\": 999}", encoding="utf-8")
    assert load_prose_identity_profile(tmp_path) is None


def test_profile_saves_revisions_and_restores_as_a_new_revision(tmp_path: Path):
    first = build_prose_identity_profile(["短句。第一版。"])
    save_prose_identity_profile(tmp_path, first)
    second = build_prose_identity_profile(["较长一点的句子，作为第二版。"])
    save_prose_identity_profile(tmp_path, second)

    versions = list_prose_identity_profile_versions(tmp_path)
    assert [item["revision"] for item in versions] == [2, 1]
    assert versions[0]["is_active"] is True
    assert versions[1]["is_active"] is False

    restore_prose_identity_profile(tmp_path, revision=1)
    active = load_prose_identity_profile(tmp_path)
    assert active is not None
    assert active["profile_id"] == first["profile_id"]
    assert active["restored_from_revision"] == 1
    assert active["revision"] == 3
    assert [item["revision"] for item in list_prose_identity_profile_versions(tmp_path)] == [3, 2, 1]


def test_quality_report_includes_profile_as_non_blocking_diagnostic():
    profile = build_prose_identity_profile(["短句。再短句。这里有一点变化。"])
    report = build_quality_report("短句。再短句。这里有一点变化。", prose_profile=profile)
    baseline = build_quality_report("短句。再短句。这里有一点变化。")
    check = report["checks"]["prose_identity"]
    assert check["pass"] is True
    assert check["blocking"] is False
    assert report["overall_pass"] == baseline["overall_pass"]


def test_profile_deviation_becomes_review_hint_but_not_a_gate():
    profile = build_prose_identity_profile(["短句。再短句。这里有一点变化。"])
    report = build_quality_report(
        "这是一个非常非常长的段落，没有对白，也没有明显的句号",
        prose_profile=profile,
    )
    check = report["checks"]["prose_identity"]
    hints = build_quality_rewrite_hints(report)
    assert check["status"] == "review"
    assert check["pass"] is True
    assert "文风档案" in hints
