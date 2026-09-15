"""Unit tests for DiffReviewSession and CommandHistory."""

from novel_agent.editing.diff_reviewer import DiffReviewSession, DiffChunkType
from novel_agent.editing.command_history import CommandHistory, TextEditCommand


def test_interactive_diff_acceptance():
    original = "第一句话。\n旧的第二句话。\n旧的第三句话。"
    suggested = "第一句话。\n新的第二句话。\n新的第三句话。"

    session = DiffReviewSession(original, suggested)
    chunks = session.chunks
    assert len(chunks) >= 2

    # Find replacement chunks
    change_chunks = [c for c in chunks if c.chunk_type != DiffChunkType.EQUAL]
    assert len(change_chunks) >= 1

    # Accept first change, reject if there are others
    first_id = change_chunks[0].chunk_id
    assert session.accept_chunk(first_id) is True

    # Render result
    result = session.render_result()
    assert "第一句话" in result
    assert "新的第二句话" in result

    # Accept all
    session.accept_all()
    assert session.render_result() == suggested

    # Reject all
    session.reject_all()
    assert session.render_result() == original


def test_command_history_undo_redo():
    history = CommandHistory()
    document = {"content": "初始正文"}

    def set_content(new_text: str):
        document["content"] = new_text

    cmd1 = TextEditCommand("改动1", set_content, "初始正文", "第一次修改")
    history.execute(cmd1)
    assert document["content"] == "第一次修改"
    assert history.can_undo is True
    assert history.can_redo is False

    cmd2 = TextEditCommand("改动2", set_content, "第一次修改", "第二次修改")
    history.execute(cmd2)
    assert document["content"] == "第二次修改"

    # Undo cmd2
    history.undo()
    assert document["content"] == "第一次修改"
    assert history.can_redo is True

    # Undo cmd1
    history.undo()
    assert document["content"] == "初始正文"
    assert history.can_undo is False

    # Redo cmd1
    history.redo()
    assert document["content"] == "第一次修改"
