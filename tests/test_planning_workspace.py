import json

from novel_agent.services.planning_workspace import build_planning_workspace
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_planning_workspace_merges_character_setup_and_runtime_state(tmp_path):
    (tmp_path / "workspace").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "protagonist": {"name": "林墨", "desire": "查清真相"},
                "macro_outline": [
                    {"arc_id": "A01", "name": "入局", "chapters": "1-12", "goal": "发现线索"}
                ],
                "world_rules": ["使用能力会失去记忆"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "assets" / "character_cards.yaml").write_text(
        "characters:\n  - name: 林墨\n    role: 主角\n  - name: 周岚\n    role: 搭档\n",
        encoding="utf-8",
    )
    store = SQLiteStateStore(tmp_path)
    store.sync_state_update(
        "003",
        {
            "characters": {"林墨": {"location": "旧城区", "emotion": "警惕"}},
            "objects": [{"id": "key", "name": "铜钥匙", "holder": "林墨"}],
            "foreshadows": [
                {"id": "F01", "title": "失踪名单", "status": "open", "description": "名单被涂改"}
            ],
            "events": [
                {"id": "E01", "summary": "林墨取得钥匙", "characters": ["林墨"]}
            ],
            "character_relations": [
                {
                    "source_char": "林墨",
                    "target_char": "周岚",
                    "relation_type": "合作",
                    "intensity": 0.6,
                }
            ],
        },
    )

    workspace = build_planning_workspace(tmp_path)

    protagonist = next(item for item in workspace.entities if item.name == "林墨")
    assert protagonist.configured["desire"] == "查清真相"
    assert protagonist.current_state["location"] == "旧城区"
    assert workspace.counts["outline"] == 1
    assert workspace.counts["object"] == 1
    assert workspace.counts["foreshadow"] == 1
    assert workspace.relations[0].label == "合作"
    assert workspace.timeline[0]["summary"] == "林墨取得钥匙"


def test_planning_workspace_returns_stable_empty_contract(tmp_path):
    workspace = build_planning_workspace(tmp_path)

    assert workspace.schema_version == 1
    assert workspace.entities == []
    assert workspace.relations == []
    assert "尚未建立完整大纲" in workspace.warnings


def test_planning_workspace_summarizes_rule_categories_instead_of_using_raw_values(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "rules.yaml").write_text(
        """
commonWords:
  - content: 愣住
    description: 避免重复
  - content: 深吸一口气
    description: 控制频次
writingTechniques: |
  - 直接承接上一场景。
  - 用具体动作推动画面。
referenceAuthors: []
""".strip(),
        encoding="utf-8",
    )

    workspace = build_planning_workspace(tmp_path)
    rules = [entity for entity in workspace.entities if entity.kind == "rule"]

    assert [entity.name for entity in rules] == ["常用词提醒", "写作技巧", "参考作者"]
    assert rules[0].summary == "2 条规则 · 愣住、深吸一口气"
    assert rules[1].summary == "2 条写作原则"
    assert rules[2].summary == "尚未配置"
    assert all(len(entity.name) < 20 for entity in rules)
