from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from novel_agent.phases.audit import AuditPhase
from novel_agent.phases.base import ChapterContext


def test_audit_paragraph_rewrite_rejects_short_candidate(tmp_path: Path):
    original = "第一段保持不变。\n\n" + ("这是需要局部修订的原始段落，包含足够篇幅。" * 8) + "\n\n第三段保持不变。"
    target = "这是需要局部修订的原始段落，包含足够篇幅。" * 8
    orchestrator = MagicMock()
    orchestrator.style_editor.edit.return_value = "短稿。"
    phase = AuditPhase(orchestrator)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True)
    ctx = ChapterContext(
        chapter_id="001",
        chapter_goal="局部重写",
        chapter_dir=tmp_path,
        scenes_dir=tmp_path / "scenes",
        reports_dir=reports_dir,
    )
    issue = {
        "target_text": target,
        "why": "需要降低模板化表达",
        "fix": "改用动作和感官",
    }

    revised, new_ctx = phase._handle_paragraph_rewrite(
        ctx,
        original,
        [issue],
        [issue],
        attempt=0,
    )

    assert revised == original
    assert any("render contract" in warning for warning in new_ctx.warnings)
    assert (reports_dir / "audit_rewrite_candidate_1_2.txt").read_text(encoding="utf-8") == "短稿。"
