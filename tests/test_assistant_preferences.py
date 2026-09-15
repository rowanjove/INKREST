from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from web.app import app
from web.deps import ProjectSession, get_project_session
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import AuthorPreference


@pytest.fixture
def client():
    return TestClient(app)


def test_assistant_preferences_store(tmp_path: Path):
    store = AssistantStore(tmp_path)
    
    # 1. Add global preference
    p1 = AuthorPreference(
        id="pref_1",
        scope="global",
        preference_type="style",
        content="喜欢短句，注重画面动作",
    )
    store.save_preference(p1)

    # 2. Add project preference
    p2 = AuthorPreference(
        id="pref_2",
        scope="project",
        project_id="proj_cyber",
        preference_type="taboo",
        content="禁用现代网络梗词",
    )
    store.save_preference(p2)

    # List for proj_cyber: should see both global and proj_cyber
    cyber_prefs = store.list_preferences(project_id="proj_cyber")
    assert len(cyber_prefs) == 2
    contents = [p.content for p in cyber_prefs]
    assert "喜欢短句，注重画面动作" in contents
    assert "禁用现代网络梗词" in contents

    # List for another project: should see global only
    other_prefs = store.list_preferences(project_id="proj_other")
    assert len(other_prefs) == 1
    assert other_prefs[0].content == "喜欢短句，注重画面动作"

    # Delete
    deleted = store.delete_preference("pref_1")
    assert deleted is True
    assert len(store.list_preferences("proj_cyber")) == 1


def test_preferences_api_endpoints(client, tmp_path):
    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        # Create preference via API
        res = client.post("/api/assistant/preferences", json={
            "content": "战斗场面强化冷兵器碰撞声",
            "preference_type": "style",
            "scope": "project"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        pref_id = data["preference"]["id"]

        # List preferences
        res_list = client.get("/api/assistant/preferences")
        assert res_list.status_code == 200
        prefs = res_list.json()["preferences"]
        assert any(p["content"] == "战斗场面强化冷兵器碰撞声" for p in prefs)

        # Delete preference
        res_del = client.delete(f"/api/assistant/preferences/{pref_id}")
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True

        # Verify deletion
        res_list2 = client.get("/api/assistant/preferences")
        assert not any(p["id"] == pref_id for p in res_list2.json()["preferences"])
    finally:
        app.dependency_overrides.pop(get_project_session, None)
