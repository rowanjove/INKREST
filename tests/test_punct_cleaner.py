from novel_agent.quality.punct_cleaner import clean_punctuation_and_typography


def test_clean_halfwidth_punctuation_in_chinese():
    raw = "林风深吸一口气,握紧手中的长剑. 他转身看向四周:没有一个人! \"你到底是谁?\"他喊道."
    cleaned = clean_punctuation_and_typography(raw)
    assert "，" in cleaned
    assert "。" in cleaned
    assert "：" in cleaned
    assert "！" in cleaned
    assert "？" in cleaned
    assert "," not in cleaned


def test_clean_repeated_punctuation():
    raw = "这怎么可能？？？他竟然突破了！！！难道真是他？！"
    cleaned = clean_punctuation_and_typography(raw)
    assert "？？？" not in cleaned
    assert "！！！" not in cleaned
    assert "？" in cleaned
    assert "！" in cleaned
    assert "！？" in cleaned or "？！" in cleaned


def test_clean_ellipses_and_dashes():
    raw = "剑光炸裂————天地变色.....一切都结束了"
    cleaned = clean_punctuation_and_typography(raw)
    assert "————" not in cleaned
    assert "——" in cleaned
    assert "....." not in cleaned
    assert "……" in cleaned


def test_cleaner_preserves_standard_chinese_ellipsis():
    raw = "他沉默了……然后转身。"

    cleaned = clean_punctuation_and_typography(raw)

    assert cleaned == raw
    assert clean_punctuation_and_typography(cleaned) == cleaned


def test_clean_excessive_blank_lines():
    raw = "第一段文字。\n\n\n\n\n第二段文字。"
    cleaned = clean_punctuation_and_typography(raw)
    assert cleaned == "第一段文字。\n\n第二段文字。"
