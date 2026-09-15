import pytest
from pathlib import Path

from plugins.script_murder.package.agents.orchestrator import ScriptMurderOrchestrator
from plugins.script_murder.package.schemas import ProjectMeta, ScriptMurderWorkspace
from plugins.script_murder.package.services.model_service import ModelService
from plugins.script_murder.package.services.playtester import PlaytestService


@pytest.fixture
def orchestrator():
    root = Path(__file__).resolve().parent.parent.parent.parent
    model_svc = ModelService(root)
    return ScriptMurderOrchestrator(model_svc)


def test_full_pipeline_orchestration(orchestrator: ScriptMurderOrchestrator):
    # 1. Brief
    brief = orchestrator.generate_brief("暴雨夜北方港口密室案", player_count=6)
    assert "title" in brief
    assert "genre" in brief

    # 2. Truth Canon
    canon = orchestrator.generate_truth_canon("暴雨夜北方港口密室案", player_count=6)
    assert canon.killer != ""
    assert canon.victim != ""
    assert len(canon.facts) >= 1

    # 3. Characters
    characters = orchestrator.generate_characters(canon, player_count=6)
    assert len(characters) == 6
    assert any(c.id == canon.killer for c in characters)

    # 4. Clues & Deductive Graph
    clues, conclusions = orchestrator.generate_clue_graph(canon, characters)
    assert len(clues) >= 2
    assert len(conclusions) >= 1

    # 5. Flow
    flow = orchestrator.generate_game_flow(canon, characters, clues)
    assert len(flow.rounds) >= 3
    assert flow.rounds[-1].vote_required is True

    # 6. Character Script with Visibility Filter
    innocent_char = next(c for c in characters if c.id != canon.killer)
    script_text = orchestrator.generate_character_script(innocent_char, canon, act=1)
    assert len(script_text) > 20
    # Ensure script writer was called with no crash

    # 7. Host Guide
    ws = ScriptMurderWorkspace(
        meta=ProjectMeta(id="sm_test", title="雾港十三号", player_count=6),
        canon=canon,
        characters=characters,
        clues=clues,
        conclusions=conclusions,
        flow=flow,
    )
    host_guide = orchestrator.generate_host_guide(ws)
    assert "复盘" in host_guide or "真相" in host_guide


def test_virtual_playtest(orchestrator: ScriptMurderOrchestrator):
    root = Path(__file__).resolve().parent.parent.parent.parent
    model_svc = ModelService(root)
    playtest_svc = PlaytestService(model_svc)

    canon = orchestrator.generate_truth_canon("暴风雪山庄命案", player_count=4)
    characters = orchestrator.generate_characters(canon, player_count=4)
    clues, conclusions = orchestrator.generate_clue_graph(canon, characters)
    flow = orchestrator.generate_game_flow(canon, characters, clues)

    ws = ScriptMurderWorkspace(
        meta=ProjectMeta(id="sm_test2", title="海妖之歌", player_count=4),
        canon=canon,
        characters=characters,
        clues=clues,
        conclusions=conclusions,
        flow=flow,
    )

    report = playtest_svc.run_virtual_playtest(ws)
    assert report.solved is True
    assert 0 <= report.solvability_score <= 100
    assert len(report.round_reasoning_log) >= 1

    # Full audit
    audit_report = playtest_svc.run_full_audit(ws)
    assert audit_report.is_valid is True
