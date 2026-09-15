import pytest
from plugins.script_murder.package.schemas import (
    CharacterKnowledgeItem,
    CharacterProfile,
    CharacterTimelineEvent,
    ClueItem,
    DeductiveConclusion,
    ProjectMeta,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)
from plugins.script_murder.package.services.validator import DeterministicValidator


def test_validator_perfect_case():
    meta = ProjectMeta(id="p1", title="完美闭环", player_count=2)
    canon = TruthCanon(
        victim="张总",
        killer="CHAR_01",
        crime_scene="办公室",
        crime_time_window=("21:00", "21:30"),
        facts=[
            TruthFact(id="F001", title="毒杀", content="张总死于氰化物中毒"),
        ],
    )
    chars = [
        CharacterProfile(
            id="CHAR_01",
            name="真凶",
            public_identity="秘书",
            timeline=[
                CharacterTimelineEvent(time="21:15", location="办公室", activity_real="下毒", activity_claimed="在走廊")
            ],
            knowledge_map=[
                CharacterKnowledgeItem(fact_id="F001", epistemic_state="knowledge", narrative_statement="知道下毒")
            ],
        ),
        CharacterProfile(
            id="CHAR_02",
            name="平民",
            public_identity="司机",
            timeline=[
                CharacterTimelineEvent(time="21:15", location="停车场", activity_real="等候", activity_claimed="等候")
            ],
        ),
    ]
    concl = DeductiveConclusion(
        id="CONCL_01",
        title="投毒结论",
        description="真凶在办公室投毒",
        supported_by_clues=["C001"],
    )
    clues = [
        ClueItem(
            id="C001",
            title="茶杯检出毒物",
            content="茶杯残余微量氰化物结晶",
            fact_refs=["F001"],
            supports_conclusions=["CONCL_01"],
        )
    ]
    ws = ScriptMurderWorkspace(
        meta=meta,
        canon=canon,
        characters=chars,
        clues=clues,
        conclusions=[concl],
    )

    validator = DeterministicValidator(ws)
    report = validator.validate_all()
    assert report.is_valid is True
    assert report.blocker_count == 0
    assert report.error_count == 0
    assert report.metrics["evidence_chain_closure_rate"] == 1.0


def test_validator_detects_spatial_timeline_conflict():
    meta = ProjectMeta(id="p2", title="时空分裂", player_count=1)
    chars = [
        CharacterProfile(
            id="CHAR_01",
            name="嫌疑人A",
            public_identity="记者",
            timeline=[
                CharacterTimelineEvent(time="21:15", location="酒吧", activity_real="喝酒", activity_claimed="喝酒"),
                CharacterTimelineEvent(time="21:15", location="仓库", activity_real="搜证", activity_claimed="搜证"),
            ],
        )
    ]
    ws = ScriptMurderWorkspace(meta=meta, characters=chars)
    validator = DeterministicValidator(ws)
    report = validator.validate_all()
    assert report.is_valid is False
    assert any(issue.code == "TIMELINE_SPATIAL_SPLIT" for issue in report.issues)


def test_validator_detects_visibility_leak():
    meta = ProjectMeta(id="p3", title="剧本泄密", player_count=2)
    canon = TruthCanon(
        victim="老船长",
        killer="CHAR_01",
        facts=[
            TruthFact(
                id="F001",
                title="绝密走私黄金案",
                content="死者秘密私藏了三箱南洋走私金条在地下室夹层",
                is_core_truth=True,
            )
        ],
    )
    # CHAR_02 is innocent and should not know about the gold
    chars = [
        CharacterProfile(id="CHAR_01", name="凶手", public_identity="大副"),
        CharacterProfile(
            id="CHAR_02",
            name="平民",
            public_identity="水手",
            knowledge_map=[],  # knows nothing about F001
            script_acts={
                "act_1": "你看到天黑了，你心里很清楚死者秘密私藏了三箱南洋走私金条，你一直在盯着地下室夹层。"
            },
        ),
    ]
    ws = ScriptMurderWorkspace(meta=meta, canon=canon, characters=chars)
    validator = DeterministicValidator(ws)
    report = validator.validate_all()
    assert report.is_valid is False
    assert any(issue.code == "VISIBILITY_LEAK" and issue.severity == "BLOCKER" for issue in report.issues)


def test_validator_detects_orphan_clue():
    meta = ProjectMeta(id="p4", title="孤儿线索", player_count=1)
    clues = [
        ClueItem(
            id="C999",
            title="一把生锈钥匙",
            content="普通铜钥匙，表面布满锈斑",
            fact_refs=[],
            supports_conclusions=[],
            is_red_herring=False,
        )
    ]
    ws = ScriptMurderWorkspace(meta=meta, clues=clues)
    validator = DeterministicValidator(ws)
    report = validator.validate_all()
    assert any(issue.code == "ORPHAN_CLUE" for issue in report.issues)
