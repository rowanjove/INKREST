"""Unit tests for CrashRecoveryManager and draft diff inspection."""

from pathlib import Path
from novel_agent.recovery.crash_recovery import CrashRecoveryManager


def test_crash_detection_flow(tmp_path: Path):
    mgr = CrashRecoveryManager(tmp_path)

    # Session 1 starts
    mgr.record_startup()
    mgr.save_draft(
        doc_id="ch-001",
        project_id="proj-alpha",
        title="第1章 惊变",
        content="窗外的雨下得很大，林野点了一根烟。",
    )

    # Simulating sudden process termination / crash (no mark_clean_shutdown call)
    # Session 2 starts: new manager detects crash
    mgr2 = CrashRecoveryManager(tmp_path)
    crash_report = mgr2.detect_unclean_shutdown()
    assert crash_report is not None
    assert crash_report.has_uncommitted_work is True
    assert len(crash_report.drafts) == 1

    draft = crash_report.drafts[0]
    assert draft.doc_id == "ch-001"
    assert "林野" in draft.content

    # Diff inspection
    original_text = "窗外的雨停了。"
    diff = mgr2.compute_diff(original_text, draft.content)
    assert "+窗外的雨下得很大" in diff
    assert "-窗外的雨停了" in diff

    # Discard draft after applying or rejecting
    assert mgr2.discard_draft("ch-001", "proj-alpha") is True
    assert len(mgr2.list_drafts()) == 0

    # Clean shutdown
    mgr2.mark_clean_shutdown()
    assert mgr2.detect_unclean_shutdown() is None
