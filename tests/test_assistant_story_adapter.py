import json
from pathlib import Path
import pytest
import yaml

from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.context.resolver import StoryContextResolver
from novel_agent.assistant.models import ActiveEditorContext, SourceType


def test_story_adapter_and_resolver(tmp_path: Path):
    # Setup mock project structure
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "project_meta.json").write_text(
        json.dumps({"title": "赛博修真录", "genre": "科幻修仙"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "chosen_title": "赛博修真录",
                "macro_outline": [
                    {
                        "arc_id": "arc_1",
                        "chapter_list": [
                            {"chapter_id": "001", "title": "初入灵网", "goal": "江炘获得黑色终端并逃离黑市"}
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "character_cards.yaml").write_text(
        yaml.safe_dump(
            {
                "characters": [
                    {
                        "id": "char_jiang",
                        "name": "江炘",
                        "fixed_profile": {"role": "主角", "core_motivation": "寻找失踪的妹妹"},
                        "must_not": ["出卖朋友"],
                    },
                    {
                        "id": "char_lin",
                        "name": "林雪",
                        "fixed_profile": {"role": "黑客情报贩子", "core_motivation": "逃离财阀控制"},
                    },
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    adapter = StoryAdapter(tmp_path)
    assert adapter.is_valid is True
    meta = adapter.get_project_meta()
    assert meta["title"] == "赛博修真录"

    ch_outline = adapter.get_chapter_outline("001")
    assert ch_outline is not None
    assert "黑色终端" in ch_outline["goal"]

    chars = adapter.get_character_cards()
    assert len(chars) == 2
    assert chars[0]["name"] == "江炘"

    # Test Resolver with ActiveEditorContext
    resolver = StoryContextResolver(adapter)
    editor_ctx = ActiveEditorContext(
        chapter_id="001",
        selected_text="江炘看着林雪，手中的终端微微发热。",
    )

    bundle = resolver.resolve(
        user_message="江炘此时知道林雪的真实身份吗？",
        editor_context=editor_ctx,
    )

    assert any(chip["id"] == "chapter_001" for chip in bundle.chips)
    assert any("江炘" in chip["label"] for chip in bundle.chips)
    assert len(bundle.citations) > 0
    assert bundle.citations[0].source_type in [SourceType.CHARACTER, SourceType.OUTLINE]
    assert "黑色终端" in bundle.formatted_prompt_block
