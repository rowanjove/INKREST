"""Tests for HWE detectors with positive and negative cases."""

from novel_agent.human_writing.detectors.dialogue import DialogueDetector
from novel_agent.human_writing.detectors.matcher import TextStructure
from novel_agent.human_writing.detectors.narration import NarrationDetector
from novel_agent.human_writing.detectors.phrase import PhraseDetector
from novel_agent.human_writing.detectors.rhythm import RhythmDetector
from novel_agent.human_writing.detectors.syntax import SyntaxDetector
from novel_agent.human_writing.rules.registry import get_rule_registry


def test_binary_contrast_positive_and_negative():
    registry = get_rule_registry()
    rules = registry.list_rules(family="staging")

    # Positive: AI style philosophical/dramatic contrast
    pos_text = "这不是一次失败，而是一次重新定义自我的机会。"
    struct = TextStructure(pos_text)
    issues = SyntaxDetector.scan(pos_text, struct, rules)
    matched_ids = [i.hwe.rule_id for i in issues]
    assert "HWE.STAGING.BINARY_CONTRAST" in matched_ids

    # Negative: factual dialogue correction should be skipped
    neg_text = "“不是三号，而是十三号。”"
    struct_neg = TextStructure(neg_text)
    issues_neg = SyntaxDetector.scan(neg_text, struct_neg, rules)
    matched_ids_neg = [i.hwe.rule_id for i in issues_neg]
    assert "HWE.STAGING.BINARY_CONTRAST" not in matched_ids_neg


def test_narration_over_explanation():
    registry = get_rule_registry()
    rules = registry.list_rules(family="narration")

    # Positive: action followed by immediate emotion labeling
    pos_text = "林默紧攥着拳头。显然他很害怕，内心的愤怒也在疯狂滋长。"
    struct = TextStructure(pos_text)
    issues = NarrationDetector.scan(pos_text, struct, rules)
    matched_ids = [i.hwe.rule_id for i in issues]
    assert "HWE.NARRATION.OVER_EXPLANATION" in matched_ids

    # Negative: pure physical action without redundant emotion explanation
    clean_text = "林默拿起茶杯喝了一口，杯壁上还残留着淡淡的茶渍。"
    struct_clean = TextStructure(clean_text)
    issues_clean = NarrationDetector.scan(clean_text, struct_clean, rules)
    assert len(issues_clean) == 0


def test_rhythm_staccato_and_triple_list():
    registry = get_rule_registry()
    rules = registry.list_rules(family="rhythm")

    # Positive staccato abuse: 5+ short sentences
    staccato_text = "风在吹。夜很黑。他站着。他咬牙。门开了。枪响了。"
    struct = TextStructure(staccato_text)
    issues = RhythmDetector.scan(staccato_text, struct, rules)
    matched_ids = [i.hwe.rule_id for i in issues]
    assert "HWE.RHYTHM.STACCATO_ABUSE" in matched_ids

    # Triple list
    triple_text = "他的眼神里包含了困惑、惊恐以及愤怒。"
    struct_triple = TextStructure(triple_text)
    issues_triple = RhythmDetector.scan(triple_text, struct_triple, rules)
    matched_ids_triple = [i.hwe.rule_id for i in issues_triple]
    assert "HWE.RHYTHM.TRIPLE_LIST_OVERUSE" in matched_ids_triple


def test_phrase_and_stock_metaphor():
    registry = get_rule_registry()
    rules = registry.list_rules(family="imagery")

    pos_text = "听到这个消息，林默喉结滚动，感觉整个人犹如热锅上的蚂蚁。"
    struct = TextStructure(pos_text)
    issues = PhraseDetector.scan(pos_text, struct, rules)
    matched_ids = [i.hwe.rule_id for i in issues]
    assert "HWE.IMAGERY.BODY_REACTION_REPEAT" in matched_ids
    assert "HWE.IMAGERY.STOCK_METAPHOR" in matched_ids


def test_dialogue_exposition_and_qa_chain():
    registry = get_rule_registry()
    rules = registry.list_rules(family="dialogue")

    # Exposition in dialogue
    dial_text = "“正如你所知道的，我们这个组织已经秘密成立了整整五百年。”"
    struct = TextStructure(dial_text)
    issues = DialogueDetector.scan(dial_text, struct, rules)
    matched_ids = [i.hwe.rule_id for i in issues]
    assert "HWE.DIALOGUE.EXPOSITION_DIALOGUE" in matched_ids
