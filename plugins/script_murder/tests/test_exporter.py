import io
import zipfile
import pytest
from plugins.script_murder.package.schemas import (
    CharacterKnowledgeItem,
    CharacterProfile,
    CharacterTimelineEvent,
    ClueItem,
    DeductiveConclusion,
    GameFlow,
    GameRound,
    ProjectMeta,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)
from plugins.script_murder.package.services.exporter import ScriptMurderExporter


def test_exporter_preflight_blocks_incomplete_project():
    incomplete_ws = ScriptMurderWorkspace(
        meta=ProjectMeta(id="p_inc", title="残缺项目"),
        canon=TruthCanon(),
    )
    exporter = ScriptMurderExporter(incomplete_ws)
    preflight = exporter.preflight_check()
    assert preflight.can_export is False
    assert preflight.blocker_count >= 1

    with pytest.raises(ValueError, match="Export blocked"):
        exporter.build_zip_bytes()


def test_exporter_builds_complete_zip_package():
    meta = ProjectMeta(id="sm_exp", title="雾港十三号", player_count=2)
    canon = TruthCanon(
        victim="陈默",
        killer="CHAR_02",
        cause_of_death="钝器重击",
        crime_time_window=("21:10", "21:25"),
        crime_scene="13号仓库",
        crime_method="滑轮配重延时装置",
        true_motive="提单勒索",
        facts=[
            TruthFact(id="F001", title="死亡判定", content="受害人颅骨骨折当场死亡", occurred_at="21:14", location="13号仓库"),
            TruthFact(id="F002", title="真凶逃逸", content="周野逃离撕破雨裤留B型血", occurred_at="21:16", location="西门"),
        ],
    )
    characters = [
        CharacterProfile(
            id="CHAR_01",
            name="林晚",
            public_identity="调查记者",
            secrets=["私自调查走私内幕"],
            timeline=[CharacterTimelineEvent(time="21:15", location="酒吧", activity_real="避雨", activity_claimed="避雨")],
            knowledge_map=[CharacterKnowledgeItem(fact_id="F001", epistemic_state="knowledge", narrative_statement="得知死者遇害")],
            script_acts={"act_1": "你冒雨冲进码头大厅，大衣已经湿透。"},
        ),
        CharacterProfile(
            id="CHAR_02",
            name="周野",
            public_identity="货代组长",
            secrets=["受害者掌握其盗卖单据"],
            timeline=[CharacterTimelineEvent(time="21:15", location="13号仓库", activity_real="触发机关", activity_claimed="在办公室")],
            knowledge_map=[
                CharacterKnowledgeItem(fact_id="F001", epistemic_state="knowledge", narrative_statement="亲自作案"),
                CharacterKnowledgeItem(fact_id="F002", epistemic_state="knowledge", narrative_statement="刮伤膝盖"),
            ],
            script_acts={"act_1": "你把断开的皮尺塞进工具包，掌心全被汗水泡发白了。"},
        ),
    ]
    concl = DeductiveConclusion(
        id="CONCL_01",
        title="西门逃逸结论",
        description="真凶自西门逃离",
        supported_by_clues=["C001"],
    )
    clues = [
        ClueItem(
            id="C001",
            title="带血纤维",
            content="西门发现深蓝尼龙纤维与B型血",
            round=1,
            location="西门",
            fact_refs=["F002"],
            supports_conclusions=["CONCL_01"],
        )
    ]
    flow = GameFlow(
        prologue="深秋雨夜，海港突发命案。",
        rounds=[
            GameRound(round_index=1, title="第1轮搜证", search_clue_ids=["C001"]),
        ],
        epilogue_killer="周野俯首认罪。",
        epilogue_escape="周野逃离港口。",
    )

    ws = ScriptMurderWorkspace(
        meta=meta,
        canon=canon,
        characters=characters,
        clues=clues,
        conclusions=[concl],
        flow=flow,
        host_guide="# 主持人手册\n\n完整案情真相...",
    )

    exporter = ScriptMurderExporter(ws)
    preflight = exporter.preflight_check()
    assert preflight.can_export is True
    assert preflight.blocker_count == 0

    # Build ZIP and verify contents
    zip_bytes = exporter.build_zip_bytes()
    assert len(zip_bytes) > 500

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        # Verify key directory entries
        assert any("00_开本主持人使用说明.md" in name for name in namelist)
        assert any("01_主持人资料/01_主持人手册.md" in name for name in namelist)
        assert any("01_主持人资料/02_二维时空总时间表.md" in name for name in namelist)
        assert any("02_角色剧本/01_林晚_角色册.md" in name for name in namelist)
        assert any("02_角色剧本/02_周野_角色册.md" in name for name in namelist)
        assert any("03_线索卡/第1轮/C001_带血纤维.md" in name for name in namelist)
        assert any("04_公共资料/01_故事背景与规则.md" in name for name in namelist)
        assert any("05_结局/游戏结局复盘.md" in name for name in namelist)
        assert any("source/workspace.json" in name for name in namelist)

        # Inspect a single character script file
        char_script = zf.read([n for n in namelist if "01_林晚" in n][0]).decode("utf-8")
        assert "你的角色：林晚" in char_script
        assert "私自调查走私内幕" in char_script
        assert "冒雨冲进码头大厅" in char_script
