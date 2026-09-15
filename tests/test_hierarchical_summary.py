import pytest
from pathlib import Path
from novel_agent.services.hierarchical_summary import assemble_hierarchical_context


def test_assemble_hierarchical_context_complete(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    chapters_dir = workspace / "chapters"
    chapters_dir.mkdir(parents=True)

    # 1. Create outline with L0 and L1
    outline = {
        "chosen_title": "星海长生仙途",
        "genre": "科幻修仙",
        "target_chapters": 100,
        "core_theme": "凡人依靠智械解析仙道，终证大道之巅",
        "worldview": "修仙界法则受微观量子纠缠限制，灵气即高能态反引力子",
        "macro_outline": [
            {
                "arc_id": "A01",
                "arc_name": "第一卷 机械觉醒",
                "start_chapter": 1,
                "end_chapter": 5,
                "goal": "筑基并取得微型反应堆",
                "turning_point": "黑风寨遭遇宗门围猎",
            },
            {
                "arc_id": "A02",
                "arc_name": "第二卷 星环试炼",
                "start_chapter": 6,
                "end_chapter": 15,
                "goal": "结成虚丹并登临天机擂台",
                "turning_point": "天机阁秘境崩塌",
            },
        ],
    }
    (workspace / "outline.json").write_text(__import__("json").dumps(outline), encoding="utf-8")

    # 2. Create previous chapters (e.g. for target chapter 7)
    for ch_id in ["004", "005", "006"]:
        cdir = chapters_dir / f"chapter_{ch_id}"
        cdir.mkdir()
        (cdir / "plan.json").write_text(
            __import__("json").dumps({"chapter_title": f"第{ch_id}章 风暴前夕", "goal": "探查情报"}),
            encoding="utf-8",
        )
        (cdir / "summary.json").write_text(
            __import__("json").dumps({"summary": f"第{ch_id}章中主角斩杀强敌并安顿难民。"}),
            encoding="utf-8",
        )

    # Assemble for chapter 7 (which is in arc 2)
    context = assemble_hierarchical_context(tmp_path, target_chapter_id="007")

    assert "星海长生仙途" in context["level0_blueprint"]
    assert "科幻修仙" in context["level0_blueprint"]
    assert "第一卷 机械觉醒（已完结）" in context["level1_arc_summary"]
    assert "第二卷 星环试炼" in context["level1_arc_summary"]
    assert "结成虚丹" in context["level1_arc_summary"]
    assert len(context["level2_recent_chapters"]) == 3
    assert "006" in [c["chapter_id"] for c in context["level2_recent_chapters"]]
    assert "【全书宏观蓝图" in context["compiled_prompt_block"]
    assert context["estimated_tokens"] > 0

    # Test with prefix format "chapter_007"
    context_prefix = assemble_hierarchical_context(tmp_path, target_chapter_id="chapter_007")
    assert context_prefix["level1_arc_summary"] == context["level1_arc_summary"]


def test_hierarchical_summary_falls_back_to_sqlite_chapter_summaries(tmp_path: Path):
    from novel_agent.state.sqlite_store import SQLiteStateStore

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "outline.json").write_text(
        __import__("json").dumps(
            {
                "chosen_title": "无磁盘摘要的书",
                "macro_outline": [
                    {
                        "arc_id": "A00",
                        "arc_name": "序卷",
                        "start_chapter": 1,
                        "end_chapter": 3,
                    },
                    {
                        "arc_id": "A01",
                        "arc_name": "第一卷",
                        "start_chapter": 4,
                        "end_chapter": 10,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = SQLiteStateStore(tmp_path)
    store.save_chapter_summary(
        "002",
        "序卷收束：旧城灯火熄灭。",
        tmp_path / "workspace" / "chapters" / "chapter_002" / "chapter_summary.md",
    )
    store.save_chapter_summary(
        "006",
        "主角在 SQLite 里记下：铜钥匙已交沈砚。",
        tmp_path / "workspace" / "chapters" / "chapter_006" / "chapter_summary.md",
    )

    context = assemble_hierarchical_context(tmp_path, target_chapter_id="007")
    assert "铜钥匙已交沈砚" in context["compiled_prompt_block"]
    assert "旧城灯火熄灭" in context["level1_arc_summary"]
    assert any(item["chapter_id"] in {"006", "6"} for item in context["level2_recent_chapters"])
