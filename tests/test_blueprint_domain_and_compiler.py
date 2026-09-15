"""Unit and integration tests for Story Blueprint Compiler and Services."""

import pytest
from novel_agent.domain.blueprint import (
    ChannelSpec,
    GenreSpec,
    StoryBlueprint,
    StoryDNA,
    TropeAtom,
    TropeRecipe,
)
from novel_agent.services.blueprint.blueprint_service import BlueprintService
from novel_agent.services.blueprint.compiler import BlueprintCompiler
from novel_agent.services.blueprint.preset_adapter import PresetAdapter
from novel_agent.services.blueprint.validator import BlueprintValidator


def test_story_blueprint_domain_models():
    dna = StoryDNA(
        channel=ChannelSpec(id="male", label="男频"),
        genres=GenreSpec(primary="仙侠", secondary=["凡人流"]),
    )
    bp = StoryBlueprint(
        id="test_bp",
        title="凡人求道录",
        dna=dna,
    )
    assert bp.id == "test_bp"
    assert bp.dna.channel.label == "男频"
    assert bp.dna.genres.primary == "仙侠"


def test_preset_adapter_loads_assets():
    adapter = PresetAdapter()
    atoms = adapter.load_atoms()
    recipes = adapter.load_recipes()

    assert len(atoms) > 0
    assert len(recipes) > 0

    types = {a.type for a in atoms}
    assert "channel" in types
    assert "genre" in types
    assert "mechanism" in types
    assert "cool_point" in types

    # Check that standard atoms exist
    atom_ids = {a.id for a in atoms}
    assert "male" in atom_ids
    assert "xitong" in atom_ids or "chongsheng" in atom_ids


def test_blueprint_validator_conflict_detection():
    validator = BlueprintValidator(
        all_atoms=[
            TropeAtom(id="wudiliu", name="无敌流", type="cool_point"),
            TropeAtom(id="shengcun", name="生存", type="cool_point"),
            TropeAtom(id="xianxia", name="仙侠", type="genre"),
            TropeAtom(id="male", name="男频", type="channel"),
        ]
    )

    # wudiliu + shengcun triggers soft tension conflict
    report = validator.validate_atom_selection(["male", "xianxia", "wudiliu", "shengcun"])
    assert report.is_valid is True  # warning doesn't invalidate
    assert any(i.code == "TENSION_OVERPOWERED_VS_SURVIVAL" for i in report.issues)


def test_blueprint_compiler_execution():
    adapter = PresetAdapter()
    compiler = BlueprintCompiler(
        all_atoms=adapter.load_atoms(),
        all_recipes=adapter.load_recipes(),
    )

    blueprint = compiler.compile(
        selected_atom_ids=["male", "xianxia", "xitong", "dalian"],
        user_inputs={
            "title": "系统助我修长生",
            "protagonist_name": "沈炼",
            "protagonist_archetype": "行事谨慎的底层修士",
        },
    )

    assert blueprint.title == "系统助我修长生"
    assert blueprint.dna.channel.id == "male"
    assert blueprint.dna.protagonist.name == "沈炼"
    assert len(blueprint.writing_guide_markdown) > 100
    assert "《系统助我修长生》故事创作蓝图" in blueprint.writing_guide_markdown
    assert len(blueprint.reader_promises) > 0
    assert len(blueprint.pacing.volumes) > 0


def test_blueprint_service_e2e(tmp_path):
    service = BlueprintService(projects_root=tmp_path)
    components = service.get_components()
    assert "channels" in components
    assert "genres" in components
    assert "mechanisms" in components
    assert "cool_points" in components

    bp = service.compile(
        selected_atom_ids=["male", "xianxia", "xitong"],
        user_inputs={"title": "测试作品"},
    )

    # Test saving into a mock project
    mock_project = tmp_path / "mock_p1"
    mock_project.mkdir()

    saved = service.save_blueprint_to_project("mock_p1", bp)
    assert saved is True
    assert (mock_project / "assets" / "story_blueprint.json").exists()
    assert (mock_project / "assets" / "writing_guide.md").exists()

    loaded = service.load_blueprint_from_project("mock_p1")
    assert loaded is not None
    assert loaded.title == "测试作品"


def test_parameter_schema_and_guide_generation():
    service = BlueprintService()
    bp = service.compile(
        selected_atom_ids=["male", "xianxia", "xitong"],
        user_inputs={
            "title": "测试系统参数",
            "mechanism_params": {
                "xitong": {
                    "consciousness": True,
                    "visibility": "protagonist_only",
                    "reward_source": "causal_exchange",
                }
            },
        },
    )

    assert "金手指参数与运行约束" in bp.writing_guide_markdown
    assert "consciousness" in bp.writing_guide_markdown
    assert bp.dna.mechanisms[0].parameters.get("consciousness") is True


def test_trope_recommender():
    service = BlueprintService()
    recs = service.recommend_atoms(["xitong"])
    assert len(recs) > 0
    # xitong should recommend dalian or shengji with high synergy score
    rec_ids = [r.atom_id for r in recs]
    assert "dalian" in rec_ids or "shengji" in rec_ids
    assert recs[0].score >= 80


def test_blueprint_compliance_auditing():
    service = BlueprintService()
    bp = service.compile(
        selected_atom_ids=["male", "xianxia", "xitong"],
        user_inputs={
            "protagonist_archetype": "极度谨慎苟道流",
        },
    )

    # 1. Auditing violation: Reader promise delayed
    report = service.check_compliance(
        blueprint=bp,
        draft_summary="平静日常，没有任何实质性进展与战力提升",
        current_chapter_index=20,
        last_payoff_chapter=1,
    )
    assert report.is_compliant is True  # Warning does not fail is_compliant
    assert any(v.category == "promise_delayed" for v in report.violations)

    # 2. Auditing violation: Hard world rule violation
    report_forbidden = service.check_compliance(
        blueprint=bp,
        draft_summary="主角无视境界差距，施展神技实现无消耗无限瞬杀大能修士",
        current_chapter_index=5,
        last_payoff_chapter=3,
    )
    assert report_forbidden.is_compliant is False
    assert any(v.category == "world_rule" and v.severity == "error" for v in report_forbidden.violations)


def test_inspiration_incubator():
    service = BlueprintService()
    result = service.incubate_idea("一个修仙界程序员用代码重构宗门护山大阵")
    assert result.original_idea != ""
    assert len(result.seeds) == 3
    for seed in result.seeds:
        assert seed.direction_title != ""
        assert len(seed.mechanisms) > 0
        assert seed.protagonist_name != ""


def test_story_mutator():
    service = BlueprintService()
    res = service.mutate_atoms(
        current_atom_ids=["male", "xianxia", "xitong", "dalian"],
        locked_dimensions=["channel", "genre"],
    )
    assert len(res.variants) == 3
    levels = [v.mutation_level for v in res.variants]
    assert "conservative" in levels
    assert "moderate" in levels
    assert "radical" in levels


def test_uniqueness_analysis():
    service = BlueprintService()
    report = service.analyze_uniqueness(["xitong", "dalian"])
    assert report.crowdedness_score >= 80
    assert len(report.suggestions) > 0
    assert any(s.category in ["career", "mechanism", "protagonist", "narrative"] for s in report.suggestions)


def test_blueprint_api_phase2():
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)

    # 1. Test incubate
    r1 = client.post("/api/blueprint/incubate", json={"idea": "算力修仙"})
    assert r1.status_code == 200
    assert len(r1.json()["seeds"]) == 3

    # 2. Test mutate
    r2 = client.post("/api/blueprint/mutate", json={"current_atoms": ["xitong", "dalian"]})
    assert r2.status_code == 200
    assert len(r2.json()["variants"]) == 3

    # 3. Test uniqueness
    r3 = client.post("/api/blueprint/analyze-uniqueness", json={"selected_atoms": ["xitong", "dalian"]})
    assert r3.status_code == 200
    assert "uniqueness_score" in r3.json()


def test_path_traversal_safety(tmp_path):
    service = BlueprintService(projects_root=tmp_path)
    bp = service.compile(selected_atom_ids=["male", "xianxia"])

    # Attempt to write outside projects_root
    assert service.save_blueprint_to_project("../../escape_test", bp) is False
    assert service.save_blueprint_to_project("..\\escape_test", bp) is False
    assert service.save_blueprint_to_project("/etc/passwd", bp) is False

    # Attempt to read outside projects_root
    assert service.load_blueprint_from_project("../../escape_test") is None
    assert service.load_blueprint_from_project("..\\escape_test") is None


def test_compliance_boundary_cases():
    service = BlueprintService()
    bp = service.compile(selected_atom_ids=["male", "xianxia"])

    # Negative chapter interval should not raise ValueError
    report = service.check_compliance(
        blueprint=bp,
        draft_summary="正常行文，无特殊情节",
        current_chapter_index=1,
        last_payoff_chapter=10,
    )
    assert report.is_compliant is True



