from novel_agent.quality.fact_ledger import audit_fact_consistency, extract_physical_facts
from novel_agent.quality.render_contract import validate_render_candidate
from novel_agent.quality.report import build_quality_report
from novel_agent.quality.settings import quality_gate_blocks


def test_extract_physical_facts():
    text = (
        "林风手持青索剑，怀揣三张破界符与一枚九转还魂丹。"
        "然而激战中他断臂受创，几近重伤！"
    )
    facts = extract_physical_facts(text)
    assert "青索剑" in facts["items"]
    assert "破界符" in facts["items"]
    assert "九转还魂丹" in facts["items"]
    assert "断臂" in facts["physical_states"]
    assert "重伤" in facts["physical_states"]


def test_fact_consistency_normal_rewrite():
    # 正常润色：去 AI 味，但保留核心道具和角色状态
    original = (
        "林风心中感到无比震惊。他从储物袋中取出一枚九转还魂丹吞服下去，"
        "他的九转还魂丹化作滚滚热流，勉强稳住了他断臂的剧痛。"
    )
    # 润色后去除了情绪词，改写了动作，但关键道具保留
    candidate = (
        "林风眉峰骤紧。他反手探入储物袋，指尖捏出一枚九转还魂丹径直咽下。"
        "丹药入喉即化，浓郁药力如铁水般封堵住断臂处崩裂的血槽。"
    )
    result = audit_fact_consistency(original, candidate)
    assert result["pass"] is True
    assert len(result["missing_items"]) == 0


def test_fact_consistency_accidental_item_drop():
    # 意外吃书：润色 Agent 把关键道具九转还魂丹给改没了
    original = (
        "林风从储物袋中取出九转还魂丹。这枚九转还魂丹是他唯一的保命底牌，"
        "他深吸一口气，九转还魂丹散发着幽香。"
    )
    # 润色稿完全没提九转还魂丹
    candidate = (
        "林风站在原地，默默调理着内息，呼吸逐渐平复下来。"
    )
    result = audit_fact_consistency(original, candidate)
    assert result["pass"] is False
    assert "九转还魂丹" in result["missing_items"]


def test_render_contract_blocks_fact_drift():
    # 验证集成到 render_contract 后的门禁表现
    original = (
        "林风握紧定风珠，连续激发定风珠的灵光，硬生生顶住了漫天狂风。"
    )
    # 篡改稿：吞掉了定风珠
    candidate = (
        "狂风肆虐。林风顶着沙暴一步步向前挪动，脚步沉重而坚定。"
    )
    contract_res = validate_render_candidate(original, candidate)
    assert contract_res["pass"] is False
    assert "fact_drift_violation" in contract_res["reasons"]


def test_render_contract_does_not_treat_metaphorical_imprint_as_item():
    original = "这件事给他留下了深刻烙印。余生每次想起，他都无法释怀。"
    candidate = "这件事令他终生难忘。余生每次忆起，他仍旧无法释怀。"

    contract_res = validate_render_candidate(original, candidate)

    assert contract_res["pass"] is True
    assert contract_res["metrics"]["fact_ledger"]["missing_items"] == []


def test_quality_report_fact_ledger_is_warning_not_a_gate():
    original = (
        "林风从储物袋中取出九转还魂丹。这枚九转还魂丹是他唯一的保命底牌，"
        "他深吸一口气，九转还魂丹散发着幽香。"
    )
    rewritten = "林风只觉得胸口发闷，在原地站了很久，什么也没拿出来。"
    report = build_quality_report(rewritten, previous_text=original, mode="report_only")
    check = report["checks"]["fact_ledger"]
    assert check["pass"] is True
    assert check["level"] == "warning"
    assert any("九转还魂丹" in item for item in check["details"])
    assert "fact_ledger" not in (report["guard_summary"].get("blocked_by") or [])
    assert quality_gate_blocks(report, "report_only") is False
