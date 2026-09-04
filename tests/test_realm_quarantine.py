from pathlib import Path

from novel_agent.quality.settings import quality_gate_blocks
from novel_agent.services.realm_quarantine import (
    RealmQuarantineManager,
    RealmSpec,
    audit_realm_quarantine,
    build_realm_quarantine_hint,
    load_realm_specs,
    parse_chapter_number,
)


def test_realm_quarantine_isolation_and_companion_whitelist():
    # 模拟两卷世界域：
    # 卷一：凡人界（1~30章），战力上限筑基
    mortal_realm = RealmSpec(
        realm_id="realm_mortal",
        name="凡人界·大乾王朝",
        chapter_start=1,
        chapter_end=30,
        max_realm_tier="筑基圆满",
    )
    # 卷二：灵界（31~100章），跨界跟随者包括灵宠和道侣
    spirit_realm = RealmSpec(
        realm_id="realm_spirit",
        name="灵界·天元大陆",
        chapter_start=31,
        chapter_end=100,
        max_realm_tier="化神圆满",
        cross_realm_companions=["吞天雀", "林清儿"],
    )

    manager = RealmQuarantineManager([mortal_realm, spirit_realm])

    # 1. 验证激活的世界域
    assert manager.get_active_realm(15).realm_id == "realm_mortal"
    assert manager.get_active_realm(45).realm_id == "realm_spirit"
    assert manager.get_active_realm(150) is None

    # 2. 验证在灵界篇时实体的隔离规则
    # 凡人界的普通客栈掌柜，应该被隔离
    assert manager.is_quarantined("李掌柜", "realm_mortal", "realm_spirit") is True
    # 凡人界的新手村村长，应该被隔离
    assert manager.is_quarantined("张村长", "realm_mortal", "realm_spirit") is True

    # 灵界本土角色，不应被隔离
    assert manager.is_quarantined("天元剑宗宗主", "realm_spirit", "realm_spirit") is False

    # 凡人界跟随主角飞升的白名单角色（灵宠“吞天雀”与道侣“林清儿”），不应被隔离！
    assert manager.is_quarantined("吞天雀", "realm_mortal", "realm_spirit") is False
    assert manager.is_quarantined("林清儿", "realm_mortal", "realm_spirit") is False


def test_realm_filter_quarantined_items():
    spirit_realm = RealmSpec(
        realm_id="realm_spirit",
        name="灵界",
        chapter_start=31,
        chapter_end=100,
        cross_realm_companions=["吞天雀"],
    )
    manager = RealmQuarantineManager([spirit_realm])

    character_list = [
        {"name": "李掌柜", "origin_realm": "realm_mortal"},
        {"name": "吞天雀", "origin_realm": "realm_mortal"},
        {"name": "灵界圣女", "origin_realm": "realm_spirit"},
    ]

    filtered = manager.filter_quarantined_items(character_list, "realm_spirit")
    filtered_names = [c["name"] for c in filtered]

    # 只有白名单伙伴“吞天雀”和灵界本土“灵界圣女”保留，凡人界的“李掌柜”被成功隔离冷冻
    assert "吞天雀" in filtered_names
    assert "灵界圣女" in filtered_names
    assert "李掌柜" not in filtered_names


def _write_realm_assets(root: Path) -> None:
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "realms.yaml").write_text(
        "realms:\n"
        "  - realm_id: realm_mortal\n"
        "    name: 凡人界\n"
        "    chapter_start: 1\n"
        "    chapter_end: 30\n"
        "    max_realm_tier: 筑基圆满\n"
        "  - realm_id: realm_spirit\n"
        "    name: 灵界\n"
        "    chapter_start: 31\n"
        "    chapter_end: 100\n"
        "    max_realm_tier: 化神圆满\n"
        "    cross_realm_companions:\n"
        "      - 吞天雀\n",
        encoding="utf-8",
    )
    (assets / "character_cards.yaml").write_text(
        "characters:\n"
        "  - id: protagonist\n"
        "    name: 林澈\n"
        "    origin_realm: realm_mortal\n"
        "  - id: innkeeper\n"
        "    name: 李掌柜\n"
        "    origin_realm: realm_mortal\n"
        "  - id: pet\n"
        "    name: 吞天雀\n"
        "    origin_realm: realm_mortal\n",
        encoding="utf-8",
    )


def test_parse_chapter_number_from_padded_id():
    assert parse_chapter_number("045") == 45
    assert parse_chapter_number("045-02") == 45
    assert parse_chapter_number("") is None


def test_load_realm_specs_from_assets(tmp_path: Path):
    _write_realm_assets(tmp_path)
    specs = load_realm_specs(tmp_path)
    assert [item.realm_id for item in specs] == ["realm_mortal", "realm_spirit"]


def test_audit_realm_quarantine_warns_but_does_not_fail(tmp_path: Path):
    _write_realm_assets(tmp_path)
    result = audit_realm_quarantine(
        "李掌柜端来一碗面，吞天雀蹲在梁上。",
        tmp_path,
        chapter_id="045",
    )
    assert result["pass"] is True
    assert result["level"] == "warning"
    assert "李掌柜" in result["details"][0]
    assert all("吞天雀" not in item for item in result["details"])


def test_realm_quarantine_hint_lists_old_world_npcs(tmp_path: Path):
    _write_realm_assets(tmp_path)
    hint = build_realm_quarantine_hint(tmp_path, "045")
    assert "灵界" in hint
    assert "李掌柜" in hint
    assert "吞天雀" not in hint


def test_context_builder_includes_quarantine_hint(tmp_path: Path):
    from unittest.mock import MagicMock

    from novel_agent.agents.context_builder import ContextBuilderAgent

    _write_realm_assets(tmp_path)
    builder = ContextBuilderAgent(tmp_path, vector_store=MagicMock())
    pack = builder.build(
        "飞升后安顿",
        {"scene_id": "045-01", "chapter_id": "045", "characters": ["林澈"]},
    )
    assert "世界域隔离" in pack
    assert "李掌柜" in pack
    assert "吞天雀" not in pack


def test_quality_report_realm_checks_stay_report_only(tmp_path: Path):
    from novel_agent.quality.report import build_quality_report

    _write_realm_assets(tmp_path)
    report = build_quality_report(
        "林澈尚在炼气一层，转眼已是金丹圆满。李掌柜还在门口招手。",
        root_dir=tmp_path,
        chapter_id="045",
        mode="report_only",
    )
    assert report["checks"]["stat_fsm"]["pass"] is True
    assert report["checks"]["stat_fsm"]["level"] == "warning"
    assert report["checks"]["realm_quarantine"]["pass"] is True
    assert report["checks"]["realm_quarantine"]["level"] == "warning"
    assert quality_gate_blocks(report, "report_only") is False
