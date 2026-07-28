"""Per-chapter pipeline trace persistence."""

from novel_agent.services.pipeline_trace import append_trace_event, load_trace, trace_path


def test_append_trace_event(tmp_path) -> None:
    chapter_dir = tmp_path / "chapter_001"
    chapter_dir.mkdir(parents=True)
    append_trace_event(chapter_dir, step="planner", status="running", chapter_id="001")
    append_trace_event(
        chapter_dir,
        step="planner",
        status="done",
        chapter_id="001",
        duration_ms=120.5,
    )
    events = load_trace(chapter_dir)
    assert len(events) == 2
    assert events[0]["step"] == "planner"
    assert events[1]["duration_ms"] == 120.5
    assert trace_path(chapter_dir).is_file()