import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from web.app import app
from web.deps import ProjectSession, get_project_session


@pytest.fixture
def client():
    return TestClient(app)


def test_list_skills_endpoint(client):
    res = client.get("/api/assistant/skills")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    skills = data["skills"]
    assert len(skills) >= 8
    commands = [s["command"] for s in skills]
    assert "/润色" in commands
    assert "/续写" in commands
    assert "/审章" in commands


def test_chat_endpoint_with_editor_context_offline(client, tmp_path):
    # Prepare a mock project
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "outline.json").write_text(
        json.dumps(
            {
                "chosen_title": "测试作品",
                "macro_outline": [
                    {
                        "arc_id": "arc_1",
                        "chapter_list": [
                            {"chapter_id": "001", "title": "序章", "goal": "开端与主角登场"}
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
        "characters:\n  - id: char_1\n    name: 李四\n    role: 主角",
        encoding="utf-8",
    )

    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        payload = {
            "message": "李四是谁？",
            "editor_context": {
                "chapter_id": "001",
                "selected_text": "李四推开了古旧的木门。",
            },
        }

        res = client.post("/api/assistant/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "reply" in data
        assert "chips" in data
        assert "citations" in data
        chip_labels = [c["label"] for c in data["chips"]]
        assert any("第 001 章" in l for l in chip_labels)
        assert len(data["citations"]) > 0
    finally:
        app.dependency_overrides.pop(get_project_session, None)


def test_patch_api_endpoints(client, tmp_path):
    ch_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    ch_dir.mkdir(parents=True)
    orig_text = "李四站在雨中。"
    (ch_dir / "chapter.txt").write_text(orig_text, encoding="utf-8")

    from novel_agent.assistant.patch.service import PatchService
    service = PatchService(tmp_path)
    patch = service.create_patch(
        project_id="test_proj",
        chapter_id="001",
        original_text=orig_text,
        proposed_text="李四撑着伞，静立在雨幕之中。",
        reason="增加动作描写",
    )

    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        # Test list patches
        res = client.get("/api/assistant/patches?chapter_id=001")
        assert res.status_code == 200
        patches = res.json()["patches"]
        assert len(patches) == 1
        assert patches[0]["id"] == patch.id

        # Test apply patch
        res_apply = client.post(f"/api/assistant/patches/{patch.id}/apply")
        assert res_apply.status_code == 200
        assert res_apply.json()["success"] is True
        assert (ch_dir / "chapter.txt").read_text(encoding="utf-8") == "李四撑着伞，静立在雨幕之中。"

        # Test revert patch
        res_revert = client.post(f"/api/assistant/patches/{patch.id}/revert")
        assert res_revert.status_code == 200
        assert res_revert.json()["success"] is True
        assert (ch_dir / "chapter.txt").read_text(encoding="utf-8") == orig_text
    finally:
        app.dependency_overrides.pop(get_project_session, None)


def test_list_tools_endpoint(client):
    res = client.get("/api/assistant/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    tools = data["tools"]
    tool_names = [t["name"] for t in tools]
    assert "get_project_meta" in tool_names
    assert "get_character" in tool_names
    assert "search_story" in tool_names
    assert "propose_text_patch" in tool_names
    assert "retry_chapter" in tool_names
    assert "rerun_gate" in tool_names


def test_runs_endpoints(client, tmp_path):
    (tmp_path / "data").mkdir(parents=True)

    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        # 1. Trigger a chat to generate a tracked run
        payload = {"message": "你好山山"}
        res = client.post("/api/assistant/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data.get("run_id") is not None
        run_id = data["run_id"]

        # 2. List runs
        res_list = client.get("/api/assistant/runs")
        assert res_list.status_code == 200
        runs = res_list.json()["runs"]
        assert len(runs) >= 1
        assert any(r["id"] == run_id for r in runs)

        # 3. Get specific run details
        res_get = client.get(f"/api/assistant/runs/{run_id}")
        assert res_get.status_code == 200
        run_detail = res_get.json()["run"]
        assert run_detail["id"] == run_id
        assert run_detail["status"] in ("completed", "failed")

        confirm_payload = {
            "action": {
                "name": "test_model_connection",
                "arguments": {},
            }
        }
        res_mismatch = client.post(f"/api/assistant/runs/{run_id}/confirm", json=confirm_payload)
        assert res_mismatch.status_code == 200
        assert res_mismatch.json()["status"] == "failed"

        from novel_agent.assistant.memory.store import AssistantStore
        from novel_agent.assistant.models import RunRecord, ToolCallStep

        store = AssistantStore(tmp_path)
        store.save_run(
            RunRecord(
                id="confirm-run",
                project_id="test_proj",
                status="requires_confirmation",
                steps=[
                    ToolCallStep(
                        tool_name="test_model_connection",
                        tool_input={},
                        tool_output={
                            "proposal": {
                                "name": "test_model_connection",
                                "arguments": {},
                            }
                        },
                        status="requires_confirmation",
                    )
                ],
            )
        )
        res_confirm = client.post("/api/assistant/runs/confirm-run/confirm", json=confirm_payload)
        assert res_confirm.status_code == 200
        confirm_data = res_confirm.json()
        assert confirm_data["status"] == "completed"
        assert len(confirm_data["steps"]) == 1
        assert confirm_data["steps"][0]["tool_name"] == "test_model_connection"
    finally:
        app.dependency_overrides.pop(get_project_session, None)


def test_threads_and_messages_endpoints(client, tmp_path):
    (tmp_path / "data").mkdir(parents=True)

    def mock_session():
        return ProjectSession(project_id="test_proj", root_dir=tmp_path)

    app.dependency_overrides[get_project_session] = mock_session
    try:
        # 1. Create a thread
        res_create = client.post("/api/assistant/threads", json={"title": "主线剧情讨论"})
        assert res_create.status_code == 200
        thread = res_create.json()["thread"]
        assert thread["title"] == "主线剧情讨论"
        thread_id = thread["id"]

        # 2. List threads
        res_list = client.get("/api/assistant/threads")
        assert res_list.status_code == 200
        threads = res_list.json()["threads"]
        assert any(t["id"] == thread_id for t in threads)

        # 3. Post a chat message attached to this thread
        chat_res = client.post(
            "/api/assistant/chat",
            json={"message": "请问江炘在第几章出场？", "thread_id": thread_id},
        )
        assert chat_res.status_code == 200
        assert chat_res.json()["thread_id"] == thread_id

        # 4. List messages in thread
        res_msgs = client.get(f"/api/assistant/threads/{thread_id}/messages")
        assert res_msgs.status_code == 200
        messages = res_msgs.json()["messages"]
        assert len(messages) >= 2  # user + assistant
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles
    finally:
        app.dependency_overrides.pop(get_project_session, None)




