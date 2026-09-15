import pytest
from plugins.script_murder.package.schemas import (
    CharacterProfile,
    CharacterKnowledgeItem,
    ClueItem,
    DeductiveConclusion,
    GameFlow,
    ProjectMeta,
    ScriptMurderWorkspace,
    TruthCanon,
    TruthFact,
)


def test_project_meta_defaults():
    meta = ProjectMeta(id="sm_001", title="雾港十三号")
    assert meta.player_count == 6
    assert meta.duration_minutes == 240
    assert "本格推理" in meta.genre
    assert meta.status == "planning"


def test_truth_canon_and_facts():
    fact = TruthFact(
        id="F001",
        title="死因判定",
        content="受害者颅骨粉碎性骨折，致死时间在21:10至21:25之间。",
        occurred_at="21:15",
        location="13号仓库",
        actors=["CHAR_01", "CHAR_02"],
    )
    canon = TruthCanon(
        victim="陈默",
        killer="CHAR_02",
        cause_of_death="钝器重击",
        crime_scene="13号保税仓库",
        facts=[fact],
    )
    assert len(canon.facts) == 1
    assert canon.facts[0].id == "F001"
    assert canon.killer == "CHAR_02"


def test_character_epistemic_quadrants():
    knowledge = CharacterKnowledgeItem(
        fact_id="F001",
        epistemic_state="lie",
        narrative_statement="声称自己当晚一直在旅馆睡觉，从未去过码头。",
        allowed_to_reveal=False,
    )
    char = CharacterProfile(
        id="CHAR_01",
        name="林晚",
        public_identity="独立调查记者",
        knowledge_map=[knowledge],
    )
    assert char.knowledge_map[0].epistemic_state == "lie"
    assert not char.knowledge_map[0].allowed_to_reveal
