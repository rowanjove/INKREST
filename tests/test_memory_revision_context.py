import json
from pathlib import Path

from novel_agent.agents.context_builder import ContextBuilderAgent
from novel_agent.state.sqlite_store import SQLiteStateStore


def test_revised_chapter_state_reaches_next_chapter_and_drops_superseded(tmp_path: Path):
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps({"scale_profile": {"scale": "medium"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    store = SQLiteStateStore(tmp_path)
    store.sync_state_update(
        "001",
        {
            "characters": {
                "linche": {"name": "林澈", "location": "出租屋", "emotion": "疲惫"}
            }
        },
    )
    store.upsert_narrative_events(
        "001",
        [{"id": "E-OLD", "summary": "林澈把信烧掉了。", "characters": ["林澈", "linche"]}],
        source_revision_id="rev-1",
    )
    store.sync_state_update(
        "001",
        {
            "characters": {
                "linche": {"name": "林澈", "location": "车站", "emotion": "警觉"}
            }
        },
    )
    store.upsert_narrative_events(
        "001",
        [{"id": "E-NEW", "summary": "林澈把信塞进大衣。", "characters": ["林澈", "linche"]}],
        source_revision_id="rev-2",
    )

    builder = ContextBuilderAgent(tmp_path)
    context = builder.build(
        "离开城市",
        {
            "scene_id": "002-01",
            "chapter_id": "002",
            "characters": ["林澈"],
            "purpose": "赶车离开",
            "entry": "车站夜雨",
            "exit": "上车",
        },
        plan={"chapter_id": "002"},
    )
    assert "车站" in context
    assert "linche" in context
    assert "烧掉" not in context
    assert "塞进大衣" in context or "E-NEW" in context
