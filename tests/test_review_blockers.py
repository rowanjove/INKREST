from pathlib import Path

from novel_agent.domain.tasks import TaskType, is_successful_empty_stop
from novel_agent.plugins.manifest import PLUGIN_ID_RE
from novel_agent.phases.generation import prepare_scene_workspace
from novel_agent.phases.base import ChapterContext
from novel_agent.plugins.sandbox import run_callable_in_process
from novel_agent.services.manuscript_workspace import read_chapter_plain_text
from novel_agent.state.sqlite_store import SQLiteStateStore
from web.helpers import SECRET_MASK, _merge_preserving_masked_secrets
from web.security import is_allowed_local_setup_host, is_trusted_local_setup_request


def test_plugin_author_example_id_matches_manifest_regex():
    assert PLUGIN_ID_RE.match("example-quality-guard")
    assert PLUGIN_ID_RE.match("example.quality-guard") is None


def test_empty_sqlite_document_does_not_resurrect_disk_draft(tmp_path: Path):
    store = SQLiteStateStore(tmp_path)
    chapter_dir = tmp_path / "workspace" / "chapters" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter_final.txt").write_text("磁盘旧稿不该复活", encoding="utf-8")
    store.create_manuscript_document(
        chapter_id="001",
        title="空章",
        content_json={"type": "doc", "content": []},
        plain_text="",
        markdown_text="",
        source="editor",
    )
    assert read_chapter_plain_text(tmp_path, "001", store=store) == ""


def test_successful_empty_stop_does_not_match_incomplete():
    assert is_successful_empty_stop("book_complete") is True
    assert is_successful_empty_stop("target_reached") is True
    assert is_successful_empty_stop("incomplete") is False
    assert is_successful_empty_stop("not completed") is False
    assert is_successful_empty_stop("unfinished") is False
    assert is_successful_empty_stop("") is False


def test_masked_secret_is_dropped_when_endpoint_changes():
    existing = {"base_url": "https://api.openai.com/v1", "api_key": "sk-live"}
    incoming = {"base_url": "https://attacker.example/v1", "api_key": SECRET_MASK}
    merged = _merge_preserving_masked_secrets(existing, incoming)
    assert merged["api_key"] == ""
    same_endpoint = _merge_preserving_masked_secrets(
        existing, {"base_url": existing["base_url"], "api_key": SECRET_MASK}
    )
    assert same_endpoint["api_key"] == "sk-live"


def test_first_party_unpicklable_hook_runs_in_thread():
    def local_hook() -> str:
        return "ran"

    local_hook.__module__ = "novel_agent.orchestrator"
    assert run_callable_in_process(local_hook, timeout_seconds=2.0) == "ran"


def test_prepare_scene_workspace_drops_stale_scenes_without_checkpoint(tmp_path: Path):
    chapter_dir = tmp_path / "chapter_001"
    scenes_dir = chapter_dir / "scenes"
    scenes_dir.mkdir(parents=True)
    leftover = scenes_dir / "scene_old.txt"
    leftover.write_text("旧场景", encoding="utf-8")
    ctx = ChapterContext(
        chapter_id="001",
        chapter_dir=chapter_dir,
        scenes_dir=scenes_dir,
        reports_dir=chapter_dir / "reports",
        plan={"scenes": [{"scene_id": "s1"}]},
        chapter_goal="goal",
    )
    prepare_scene_workspace(ctx)
    assert leftover.exists() is False


def test_local_setup_host_allowlist():
    assert is_allowed_local_setup_host("127.0.0.1") is True
    assert is_allowed_local_setup_host("localhost") is True
    assert is_allowed_local_setup_host("evil.example") is False


class _DummyRequest:
    def __init__(self, headers):
        self.headers = headers


def test_local_setup_rejects_foreign_host(monkeypatch):
    from web.security import LOCAL_SETUP_HEADER, LOCAL_SETUP_HEADER_VALUE

    request = _DummyRequest(
        {
            LOCAL_SETUP_HEADER: LOCAL_SETUP_HEADER_VALUE,
            "host": "evil.example:8000",
            "sec-fetch-site": "same-origin",
        }
    )
    assert is_trusted_local_setup_request(request) is False


def test_heartbeat_preserves_control_action(tmp_path: Path):
    store = SQLiteStateStore(tmp_path)
    repo = store.task_repository
    repo.create_task(
        task_id="task-hb",
        project_id="book-1",
        task_type=TaskType.CHAPTER,
        payload={"chapter_id": "001"},
    )
    claimed = repo.claim_task("task-hb", lease_seconds=30)
    assert claimed is not None
    started = repo.start_task("task-hb", claimed.claim_token or "")
    repo.request_control("task-hb", "pause_requested")
    updated = repo.heartbeat(
        "task-hb",
        started.claim_token or claimed.claim_token or "",
        checkpoint={"progress": {"step": "writer"}},
    )
    assert (updated.checkpoint or {}).get("control_action") == "pause_requested"
    assert (updated.checkpoint or {}).get("progress", {}).get("step") == "writer"
    repo.request_control("task-hb", "cancel_requested")
    after_cancel = repo.heartbeat(
        "task-hb",
        started.claim_token or claimed.claim_token or "",
        checkpoint={"progress": {"step": "writer"}, "control_action": "pause_requested"},
    )
    assert (after_cancel.checkpoint or {}).get("control_action") == "cancel_requested"
