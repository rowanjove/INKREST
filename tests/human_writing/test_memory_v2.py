"""Unit tests for Longform Memory 2.0 (PRD §19, §58)."""

import pytest
from novel_agent.human_writing.memory import (
    extract_expression_entries_v2,
    analyze_sliding_windows,
    detect_chapter_ending_fingerprint_repetition,
    analyze_dialogue_voice_drift,
)


def test_extract_expression_entries_v2_expanded_categories():
    """Verify that all expanded categories in PRD §19 are accurately extracted."""
    text = (
        "清晨的阳光洒在长街上。\n"
        "林默冷笑道：“这并不是巧合，而是有人蓄意为之。”\n"
        "他深吸了一口气，喉结滚动，瞳孔微缩，如坠冰窟。\n"
        "换句话说，危险已经降临。\n"
        "夜幕笼罩下，新的风暴已然悄然拉开序幕。"
    )
    entries = extract_expression_entries_v2(text, chapter_id="10")
    kinds = {e.kind for e in entries}

    assert "sentence_opening" in kinds
    assert "dialogue_tag" in kinds
    assert "syntax_pattern" in kinds
    assert "body_reaction" in kinds
    assert "emotion_reaction" in kinds
    assert "imagery" in kinds
    assert "author_summary" in kinds
    assert "chapter_opening" in kinds
    assert "chapter_closing" in kinds


def test_sliding_window_saturation_detection():
    """Verify multi-window counts and saturation flagging (PRD §19.1)."""
    curr_text = "林默喉结滚动，指尖发白。"
    curr_entries = extract_expression_entries_v2(curr_text, chapter_id="15")

    # Simulate historical entries
    historical = [
        # In chapter 14 (dist = 1 <= 3)
        {"kind": "body_reaction", "normalized": "喉结滚动", "chapter_id": "14", "text": "喉结滚动"},
        # In chapter 13 (dist = 2 <= 3)
        {"kind": "body_reaction", "normalized": "喉结滚动", "chapter_id": "13", "text": "喉结微动"},
        # In chapter 11 (dist = 4 <= 10)
        {"kind": "body_reaction", "normalized": "喉结滚动", "chapter_id": "11", "text": "喉结上下滚动"},
        # In chapter 1 (dist = 14 > 10)
        {"kind": "body_reaction", "normalized": "指尖发白", "chapter_id": "1", "text": "指尖发白"},
    ]

    diagnostics = analyze_sliding_windows(curr_entries, historical, current_chapter_id="15")
    diag_map = {d.expression: d for d in diagnostics}

    assert "喉结滚动" in diag_map
    diag_throat = diag_map["喉结滚动"]
    assert diag_throat.window_3_count == 2
    assert diag_throat.window_10_count == 3
    assert diag_throat.whole_book_count == 3
    assert diag_throat.is_saturated is True  # window_3 >= 2

    # "指尖发白" only appears in chapter 1
    if "指尖发白" in diag_map:
        diag_finger = diag_map["指尖发白"]
        assert diag_finger.window_3_count == 0
        assert diag_finger.window_10_count == 0
        assert diag_finger.whole_book_count == 1
        assert diag_finger.is_saturated is False


def test_chapter_ending_fingerprint_repetition():
    """Verify that identical chapter endings in recent chapters are caught (PRD §58.3)."""
    current_chap = "他站在窗前眺望，新的风暴已然悄然拉开序幕。"
    preceding = [
        ("1", "战斗结束了，一切恢复了平静。"),
        ("2", "夜幕笼罩下，属于他的时代悄然拉开序幕。"),
    ]

    issues = detect_chapter_ending_fingerprint_repetition(current_chap, preceding)
    assert len(issues) >= 1
    assert issues[0].type == "HWE.LONGFORM.CHAPTER_ENDING_REPEAT"
    assert "跨章节连续" in issues[0].why
    assert "2" in issues[0].why


def test_dialogue_voice_drift_detection():
    """Verify detection of voice collapse and style drift across dialogues (PRD §58.5)."""
    # Character with short-sentence style profile
    profile = {
        "style": "短句、精炼果断，禁止冗长抒情",
    }
    # Text where character produces verbose, drawn-out monologue
    text = (
        "林默看着众人说道：“如果我们现在还不立刻采取最果断的行动，那么在接下来的整整三天之内，"
        "我们所苦心经营的一切成果都将彻底化为灰烬，这是无论如何都绝对不能被接受的惨痛代价！”"
    )

    result = analyze_dialogue_voice_drift(text, character_name="林默", baseline_profile=profile)
    assert result["utterances_count"] == 1
    assert result["avg_sentence_length"] > 35
    assert result["drift_detected"] is True
    assert any("短句精炼" in r for r in result["drift_reasons"])
