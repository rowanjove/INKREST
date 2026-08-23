from __future__ import annotations

import json

from novel_agent.services.manuscript_workspace import _quality_rewrite_candidate


def test_quality_candidate_context_is_bounded_and_diagnostic_only(tmp_path):
    reports = tmp_path / "workspace" / "chapters" / "chapter_001" / "reports"
    reports.mkdir(parents=True)
    candidate = "候选稿。" * 1000
    (reports / "quality_rewrite_candidate.txt").write_text(candidate, encoding="utf-8")
    (reports / "quality_rewrite_candidate.json").write_text(
        json.dumps(
            {
                "chapter_id": "001",
                "accepted": False,
                "status": "rejected",
                "reasons": ["candidate_too_short"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _quality_rewrite_candidate(tmp_path, "001")

    assert result["available"] is True
    assert len(result["preview"]) == 1600
    assert result["preview_truncated"] is True
    assert result["metadata"]["accepted"] is False
    assert result["artifact"] == "reports/quality_rewrite_candidate.txt"
