from novel_agent.domain.stat_fsm import (
    ItemLedger,
    RealmLadder,
    audit_realm_transitions,
    extract_mentioned_ranks,
)


def test_realm_ladder_normal_progression():
    ladder = RealmLadder()

    # 单级合法进阶：炼气一层 -> 炼气二层
    ok, msg = ladder.validate_transition("炼气一层", "炼气二层")
    assert ok is True

    # 突破大境界前期：炼气九层 -> 炼气圆满 -> 筑基初期
    ok, msg = ladder.validate_transition("炼气九层", "炼气圆满")
    assert ok is True
    ok, msg = ladder.validate_transition("炼气圆满", "筑基初期")
    assert ok is True


def test_realm_ladder_blocks_illegal_jump():
    ladder = RealmLadder()

    # 非法越级：从炼气一层直接跳跃至筑基初期或金丹
    ok, msg = ladder.validate_transition("炼气一层", "筑基初期")
    assert ok is False
    assert "非法越级跳跃" in msg

    ok, msg = ladder.validate_transition("筑基初期", "元婴初期")
    assert ok is False
    assert "非法越级跳跃" in msg


def test_realm_ladder_demotion_rules():
    ladder = RealmLadder()

    # 未授权跌落：金丹初期跌至筑基初期
    ok, msg = ladder.validate_transition("金丹初期", "筑基初期", allow_drop=False)
    assert ok is False
    assert "非法修为倒退" in msg

    # 遭遇重伤废功等明确事件授权跌落
    ok, msg = ladder.validate_transition("金丹初期", "筑基初期", allow_drop=True)
    assert ok is True
    assert "修为倒退" in msg


def test_item_ledger_consumption():
    ledger = ItemLedger()
    ledger.add_item("破界符", 2)
    ledger.add_item("九转还魂丹", 1)

    # 正常消耗 1 张破界符
    ok, msg = ledger.consume_item("破界符", 1)
    assert ok is True
    assert ledger.inventory["破界符"] == 1

    # 再次消耗 1 张破界符
    ok, msg = ledger.consume_item("破界符", 1)
    assert ok is True
    assert ledger.inventory["破界符"] == 0

    # 虚空消耗：库存为 0 仍要消耗，必须拦截
    ok, msg = ledger.consume_item("破界符", 1)
    assert ok is False
    assert "道具不足" in msg


def test_extract_mentioned_ranks_prefers_longer_match():
    text = "他从炼气一层抬头，对面站着金丹圆满的长老。"
    ranks = extract_mentioned_ranks(text)
    assert ranks == ["炼气一层", "金丹圆满"]


def test_audit_realm_transitions_is_report_only_warning():
    text = "林澈尚在炼气一层，下一息已踏入金丹圆满。"
    result = audit_realm_transitions(text)
    assert result["pass"] is True
    assert result["level"] == "warning"
    assert any("越级" in item for item in result["details"])


def test_audit_realm_transitions_allows_legal_step():
    text = "他从炼气九层稳住气息，终于踏入炼气圆满。"
    result = audit_realm_transitions(text)
    assert result["pass"] is True
    assert result["level"] == "none"
    assert result["details"] == []
