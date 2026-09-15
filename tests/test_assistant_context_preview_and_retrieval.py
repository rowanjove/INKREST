import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from web.app import app
from web.deps import ProjectSession, get_project_session
from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.context.resolver import StoryContextResolver
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import ActiveEditorContext, AuthorPreference


@pytest.fixture
def client():
    return TestClient(app)


def test_story_retrieval_and_future_contamination_prevention(tmp_path: Path):
    # Setup mock chapter texts
    ch1_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    ch1_dir.mkdir(parents=True)
    (ch1_dir / "chapter.txt").write_text("江炘在地下黑市第一次买到了黑色终端，表面泛着幽蓝微光。", encoding="utf-8")

    ch5_dir = tmp_path / "workspace" / "chapters" / "chapter_005"
    ch5_dir.mkdir(parents=True)
    (ch5_dir / "chapter.txt").write_text("江炘发现黑色终端里藏有城南实验室的秘密坐标。", encoding="utf-8")

    adapter = StoryAdapter(tmp_path)

    # 1. Search when author is at chapter 2 (before_chapter="002"):
    # Must find Chapter 1, but must NOT leak Chapter 5!
    res_at_ch2 = adapter.search_story_memory("黑色终端", before_chapter="002")
    assert len(res_at_ch2) == 1
    assert res_at_ch2[0]["source_chapter"] == "001"
    assert "黑市" in res_at_ch2[0]["text"]
    assert "城南实验室" not in res_at_ch2[0]["text"]

    # 2. Search when author is at chapter 6:
    res_at_ch6 = adapter.search_story_memory("黑色终端", before_chapter="006")
    chapters_found = [r["source_chapter"] for r in res_at_ch6]
    assert "001" in chapters_found
    assert "005" in chapters_found


def test_context_preview_and_budget_breakdown(client, tmp_path):
    # Setup author preferences
    store = AssistantStore(tmp_path)
    store.save_preference(
        AuthorPreference(
            id="p_test",
            scope="global",
            content="第三人称有限视角，对白保持隐忍克制",
        )
    )

    # Setup chapter 1 text
    ch1_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    ch1_dir.mkdir(parents=True)
    (ch1_dir / "chapter.txt").write_text("雨夜的霓虹灯刺破迷雾。", encoding="utf-8")

    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        payload = {
            "message": "帮我润色一下这句动作描写",
            "editor_context": {
                "chapter_id": "001",
                "selected_text": "他拔出了激光短刃。",
                "cursor_before_text": "迷雾越来越浓。",
            },
            "skill_id": "polish",
        }
        res = client.post("/api/assistant/context/preview", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "budget_breakdown" in data
        assert "chips" in data
        budget = data["budget_breakdown"]
        assert budget["editor_selection"] > 0
        assert budget["author_preferences"] > 0
        assert "total_estimated" in budget

        # Chips must reflect selection, chapter, and preference
        chip_types = [c["type"] for c in data["chips"]]
        assert "selection" in chip_types
        assert "preference" in chip_types
        assert "chapter" in chip_types
    finally:
        app.dependency_overrides.pop(get_project_session, None)
